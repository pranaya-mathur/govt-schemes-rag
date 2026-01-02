from src.graph import app


def test_discovery():
    """Test scheme discovery intent"""
    result = app.invoke({
        "query": "what are the subsidy schemes for manufacturing?"
    })
    print(f"Intent: {result.get('intent')}")
    print(f"Answer: {result['answer']}")
    assert result.get('intent') == 'DISCOVERY'


def test_eligibility():
    """Test eligibility check intent"""
    result = app.invoke({
        "query": "am I eligible for PMEGP if I'm 25 years old?"
    })
    print(f"Intent: {result.get('intent')}")
    print(f"Answer: {result['answer']}")
    assert result.get('intent') == 'ELIGIBILITY'


def test_benefits():
    """Test benefits query intent"""
    result = app.invoke({
        "query": "how much subsidy can I get from startup india?"
    })
    print(f"Intent: {result.get('intent')}")
    print(f"Answer: {result['answer']}")
    assert result.get('intent') == 'BENEFITS'


if __name__ == "__main__":
    print("Testing Discovery...")
    test_discovery()
    
    print("\nTesting Eligibility...")
    test_eligibility()
    
    print("\nTesting Benefits...")
    test_benefits()
    
    print("\n✓ All tests passed!")
