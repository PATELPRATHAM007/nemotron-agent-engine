---
name: clean-architecture
category: architecture
description: Layered clean architecture, domain isolation, and dependency inversion.
keywords: [architecture, domain, layer, dependency, service, repository, solid]
---

# Clean Architecture & Layering Skill

## 1. Direction of Dependencies
- Presentation (Routes) -> Business Services -> Domain Core -> Infrastructure.
- Domain Core and Intelligence layers must NEVER import from presentation controllers or routes.

## 2. Interface Segregation
- Define abstract interfaces or protocols for external dependencies.
- Pass repositories via dependency injection.
