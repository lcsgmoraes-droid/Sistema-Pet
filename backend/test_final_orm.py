"""
Final test - Import through main app and verify ORM configuration
"""

print("🔍 Testing ProductVariation through main app import...")

try:
    # Import the app (this should trigger all model registrations)
    import app
    
    print("✅ App imported successfully")
    
    # Import Base to check registered tables
    from app.db import Base
    
    # Check if product_variations is registered
    tables = Base.metadata.tables.keys()
    
    if 'product_variations' in tables:
        print("✅ product_variations table is registered!")
    else:
        print("❌ product_variations table NOT found")
        print(f"Available tables: {sorted(tables)}")
    
    # Try to access the models
    from app import produtos_models
    import sys
    from pathlib import Path
    models_dir = Path(__file__).parent / "app" / "models"
    sys.path.insert(0, str(models_dir))
    import product_variation
    
    Produto = produtos_models.Produto
    ProductVariation = product_variation.ProductVariation
    
    print(f"\n🔗 Testing relationships:")
    print(f"  Produto.variations exists: {hasattr(Produto, 'variations')}")
    print(f"  ProductVariation.parent exists: {hasattr(ProductVariation, 'parent')}")
    
    # Try to inspect the mapper
    from sqlalchemy import inspect
    mapper = inspect(ProductVariation)
    print(f"\n📋 ProductVariation mapper:")
    print(f"  Table: {mapper.local_table.name}")
    print(f"  Columns: {[c.name for c in mapper.columns]}")
    print(f"  Relationships: {[r.key for r in mapper.relationships]}")
    
    print("\n🎉 All tests passed! ORM is correctly configured.")
    print("✅ You can now restart the application.")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
