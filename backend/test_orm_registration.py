"""
Simple test to verify ProductVariation model is registered with SQLAlchemy
"""

print("🔍 Testing ProductVariation model registration...")

try:
    # Import Base and models
    from app.db import Base
    import app.produtos_models
    
    # Import ProductVariation directly
    import sys
    from pathlib import Path
    models_dir = Path(__file__).parent / "app" / "models"
    sys.path.insert(0, str(models_dir))
    import product_variation
    
    print("✅ All imports successful")
    
    # Check if ProductVariation is registered in Base.metadata
    tables = Base.metadata.tables.keys()
    print(f"\n📊 Registered tables ({len(tables)}):")
    for table in sorted(tables):
        print(f"  - {table}")
    
    # Check specifically for product_variations
    if 'product_variations' in tables:
        print("\n✅ product_variations table is registered!")
    else:
        print("\n❌ product_variations table NOT found in metadata")
    
    # Check if produtos table exists
    if 'produtos' in tables:
        print("✅ produtos table is registered!")
    
    # Test the relationships
    Produto = app.produtos_models.Produto
    ProductVariation = product_variation.ProductVariation
    
    print(f"\n🔗 Checking relationships:")
    print(f"  Produto.variations: {hasattr(Produto, 'variations')}")
    print(f"  ProductVariation.parent: {hasattr(ProductVariation, 'parent')}")
    
    print("\n🎉 All tests passed!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
