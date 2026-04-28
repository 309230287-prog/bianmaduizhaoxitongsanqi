from product_code_mapper.excel.field_confirmation import (
    FieldConfirmation,
    FieldConfirmationError,
    suggest_company_mapping,
    suggest_customer_mapping,
)


def test_suggest_customer_mapping_finds_product_name():
    conf = suggest_customer_mapping(["品名", "规格", "单位"])
    assert conf.get_column_for("商品名称") == "品名"
    assert conf.get_column_for("规格") == "规格"


def test_suggest_company_mapping_finds_code_and_name():
    conf = suggest_company_mapping(["SPUID", "SPU名称", "品牌名称", "规格型号"])
    assert conf.get_column_for("商品编码") == "SPUID"
    assert conf.get_column_for("商品名称") == "SPU名称"
    assert conf.get_column_for("品牌") == "品牌名称"


def test_missing_customer_name_is_required():
    conf = suggest_customer_mapping(["类别", "备注"])
    missing = conf.missing_required_fields()
    assert "商品名称" in missing


def test_missing_company_name_and_code_are_required():
    conf = suggest_company_mapping(["类别", "备注"])
    missing = conf.missing_required_fields()
    assert "商品编码" in missing
    assert "商品名称" in missing


def test_unknown_columns_marked_ignored():
    conf = suggest_customer_mapping(["品名", "奇怪列", "另一个"])
    ignored = [m for m in conf.mappings if m.importance_level == "ignored"]
    assert len(ignored) >= 2


def test_get_column_for_returns_none_for_missing():
    conf = suggest_customer_mapping(["品名"])
    assert conf.get_column_for("品牌") is None


def test_confirm_sets_flag():
    conf = suggest_customer_mapping(["品名", "规格"])
    assert not conf.is_confirmed
    conf.confirm()
    assert conf.is_confirmed


def test_active_mappings_excludes_ignored():
    conf = suggest_customer_mapping(["品名", "奇怪列"])
    active = conf.active_mappings()
    assert all(m.importance_level != "ignored" for m in active)


def test_to_dicts_matches_count():
    conf = suggest_customer_mapping(["品名", "规格", "单位"])
    dicts = conf.to_dicts()
    assert len(dicts) == 3
    assert dicts[0]["business_field"] == "商品名称"
    assert dicts[0]["column_name"] == "品名"
