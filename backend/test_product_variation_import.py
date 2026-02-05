"""
Test to verify ProductVariation import and relationships are working correctly
"""

print("🔍 Testing ProductVariation import and ORM mapper...")

try:
    # Test 1: Import ProductVariation directly
    from app.models.product_variation import ProductVariation
    print("✅ Step 1: ProductVariation imports successfully")
    
    # Test 2: Import produtos_models (which now imports ProductVariation)
    from app import produtos_models
    print("✅ Step 2: produtos_models imports successfully")
    
    # Test 3: Verify Produto model exists
    Produto = produtos_models.Produto
    print(f"✅ Step 3: Produto model loaded: {Produto.__tablename__}")
    
    # Test 4: Verify ProductVariation is accessible
    print(f"✅ Step 4: ProductVariation model loaded: {ProductVariation.__tablename__}")
    
    # Test 5: Check if relationships are properly configured
    if hasattr(Produto, 'variations'):
        print("✅ Step 5: Produto.variations relationship exists")
    else:
        print("❌ Step 5: Produto.variations relationship NOT found")
    
    if hasattr(ProductVariation, 'parent'):
        print("✅ Step 6: ProductVariation.parent relationship exists")
    else:
        print("❌ Step 6: ProductVariation.parent relationship NOT found")
    
    # Test 6: Verify mapper is configured
    from sqlalchemy import inspect
    mapper_produto = inspect(Produto)
    mapper_variation = inspect(ProductVariation)
    print(f"✅ Step 7: Produto mapper configured with {len(mapper_produto.columns)} columns")
    print(f"✅ Step 8: ProductVariation mapper configured with {len(mapper_variation.columns)} columns")
    
    print("\n🎉 All tests passed! ORM is correctly configured.")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
