def test_recommendation_response_schema_fields():
    from backend.app import RecommendationResponse
    fields = set(RecommendationResponse.model_fields.keys()) if hasattr(RecommendationResponse, 'model_fields') else set(RecommendationResponse.model_fields_set)  # pydantic v2/v1
    # Required new fields
    assert 'position_size_usd' in fields
    assert 'position_size_pct' in fields
    # Removed legacy fields
    assert 'suggested_position_size' not in fields
    assert 'position_size_units' not in fields
    assert 'position_notional' not in fields


