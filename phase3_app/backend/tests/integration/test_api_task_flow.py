from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import Workbook, load_workbook

from product_code_mapper.api.app import create_app


def test_api_runs_task_and_exports_excel():
    client = TestClient(create_app())

    company_response = client.post(
        "/catalog/company/import",
        files={
            "file": (
                "我司商品库.xlsx",
                _workbook_bytes(
                    ["商品编码", "商品名称", "品牌", "规格", "单位"],
                    [["P1", "海天金标生抽", "海天", "500ml", "瓶"]],
                ),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert company_response.status_code == 200
    assert company_response.json()["imported_count"] == 1

    task_response = client.post(
        "/tasks",
        files={
            "file": (
                "客户商品库.xlsx",
                _workbook_bytes(
                    ["商品名称", "品牌", "规格", "单位"],
                    [
                        ["海天金标生抽", "海天", "500ml", "瓶"],
                        ["番茄酱", "", "500g", "瓶"],
                    ],
                ),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert task_response.status_code == 200
    task_id = task_response.json()["task_id"]
    assert task_response.json()["customer_count"] == 2

    start_response = client.post(f"/tasks/{task_id}/start")
    assert start_response.status_code == 200
    assert start_response.json()["status"] == "completed"
    assert start_response.json()["metrics"]["auto_code_count"] == 1

    status_response = client.get(f"/tasks/{task_id}/status")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "completed"

    export_response = client.get(f"/tasks/{task_id}/export")
    assert export_response.status_code == 200

    workbook = load_workbook(BytesIO(export_response.content))
    assert workbook.sheetnames == ["对照结果总表", "详细证据表", "统计汇总表"]
    summary_sheet = workbook["对照结果总表"]
    headers = [cell.value for cell in summary_sheet[1]]
    product_code_column = headers.index("我司商品编码") + 1
    assert summary_sheet.cell(row=2, column=product_code_column).value == "P1"


def _workbook_bytes(headers: list[str], rows: list[list[str]]) -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(headers)
    for row in rows:
        worksheet.append(row)

    stream = BytesIO()
    workbook.save(stream)
    return stream.getvalue()
