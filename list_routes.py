#!/usr/bin/env python
"""Script para listar todas as rotas da aplicação Flask."""

from app import create_app

app = create_app()

print("\n" + "="*70)
print("ROTAS DISPONÍVEIS NA APLICAÇÃO")
print("="*70 + "\n")

# Listar todas as rotas
routes = []
for rule in app.url_map.iter_rules():
    if rule.endpoint != 'static':
        methods = ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
        routes.append({
            'endpoint': rule.endpoint,
            'methods': methods,
            'rule': str(rule)
        })

# Ordenar por rota
routes.sort(key=lambda x: x['rule'])

# Exibir em formato tabular
print(f"{'ROTA':<40} {'MÉTODOS':<15} {'ENDPOINT':<30}")
print("-" * 70)
for route in routes:
    print(f"{route['rule']:<40} {route['methods']:<15} {route['endpoint']:<30}")

print("\n" + "="*70)
print(f"Total: {len(routes)} rotas registadas")
print("="*70 + "\n")

print("INFORMAÇÕES IMPORTANTES:")
print("-" * 70)
print("✓ /admin → Redireciona para /admin/login se não autenticado")
print("✓ /admin/login → Página de login do administrador")
print("✓ /admin/logout → Logout do administrador")
print("✓ /admin/property/add → Adicionar novo imóvel")
print("✓ /admin/property/edit/<id> → Editar imóvel")
print("✓ /admin/property/delete/<id> → Apagar imóvel")
print("\nCREDENCIAIS PADRÃO:")
print("  - Usuário: admin")
print("  - Senha: admin123")
print("-" * 70 + "\n")
