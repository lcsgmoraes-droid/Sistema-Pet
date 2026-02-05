from app.auth import hash_password

senha_hash = hash_password('test123')
print(senha_hash)
