"""Send concurrent recommendation requests and report latency and throughput."""

import argparse
import json
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


def run_load_test(
	base_url="http://127.0.0.1:5000",
	user_ids=None,
	requests_per_user=5,
	timeout=10,
):
	"""Run synchronized user threads and return aggregate request statistics."""
	if user_ids is None:
		user_ids = list(range(1, 11))
	if not user_ids:
		raise ValueError("At least one user ID is required")
	if requests_per_user <= 0:
		raise ValueError("requests_per_user must be positive")

	start_barrier = threading.Barrier(len(user_ids))
	results = []
	results_lock = threading.Lock()

	def request_as_user(user_id):
		"""Make the configured number of requests for one simulated user."""
		user_results = []
		start_barrier.wait()
		for _ in range(requests_per_user):
			started = time.perf_counter()
			status = None
			try:
				url = f"{base_url.rstrip('/')}/recommend/{user_id}?limit=5"
				with urlopen(url, timeout=timeout) as response:
					status = response.status
					response.read()
			except HTTPError as error:
				status = error.code
			except (URLError, TimeoutError):
				status = 0
			user_results.append((time.perf_counter() - started, status))
		with results_lock:
			results.extend(user_results)

	threads = [
		threading.Thread(target=request_as_user, args=(user_id,))
		for user_id in user_ids
	]
	started = time.perf_counter()
	for thread in threads:
		thread.start()
	for thread in threads:
		thread.join()
	wall_seconds = time.perf_counter() - started

	request_count = len(results)
	success_count = sum(200 <= status < 300 for _, status in results)
	average_latency_ms = (
		sum(latency for latency, _ in results) * 1000 / request_count
		if request_count
		else 0.0
	)
	requests_per_second = success_count / wall_seconds if wall_seconds else 0.0
	stats = {
		"concurrent_users": len(user_ids),
		"requests_per_user": requests_per_user,
		"total_requests": request_count,
		"successful_requests": success_count,
		"failed_requests": request_count - success_count,
		"average_latency_ms": average_latency_ms,
		"requests_per_second": requests_per_second,
		"elapsed_seconds": wall_seconds,
	}
	print(json.dumps(stats, indent=2))
	return stats


def main():
	"""Parse load-test options and run the threaded request simulation."""
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--base-url", default="http://127.0.0.1:5000")
	parser.add_argument("--user-ids", default="1,2,3,4,5,6,7,8,9,10")
	parser.add_argument("--requests-per-user", type=int, default=5)
	parser.add_argument("--timeout", type=float, default=10)
	args = parser.parse_args()
	user_ids = [int(value.strip()) for value in args.user_ids.split(",") if value.strip()]
	run_load_test(
		base_url=args.base_url,
		user_ids=user_ids,
		requests_per_user=args.requests_per_user,
		timeout=args.timeout,
	)


if __name__ == "__main__":
	main()