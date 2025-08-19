# import pytest

# # @pytest.hookimpl(hookwrapper=True)
# def pytest_runtest_makereport(item, call):
#     # Capture logs in the test report
#     outcome = yield
#     report = outcome.get_result()
#     if call.when == "call":
#         report.longrepr = getattr(item, "captured_log", None)

# @pytest.fixture(autouse=True)
# def capture_logs(request, caplog):
#     # Store captured logs on the test item
#     yield
#     request.node.captured_log = caplog.text

# # def pytest_html_results_table_header(cells):
# #     """
# #     Customize the HTML report header to include a column for logs.
# #     """
# #     cells.insert(2, "Captured Logs")  # Insert a new column for logs

# # def pytest_html_results_table_row(report, cells):
# #     """
# #     Add captured logs to the HTML report.
# #     Ensure the number of cells matches the header definition to prevent index errors.
# #     """
# #     if hasattr(report, "longrepr") and report.longrepr:
# #         captured_logs = f"<pre>{report.longrepr}</pre>"
# #     else:
# #         captured_logs = "No logs captured."

# #     cells.insert(2, captured_logs)  # Insert the logs into the corresponding cell

# #     # Ensure the length of cells matches the number of columns in the header
# #     expected_columns = len(cells)
# #     while len(cells) < expected_columns:
# #         cells.append("")
