# CSV2GEO API Project Guide

## Overview
Public API documentation, OpenAPI specification, SDKs, and examples for the CSV2GEO geocoding service.

**Company:** Scale Campaign
**Product:** CSV2GEO
**Contact:** admin@csv2geo.com

## Git Workflow
**Never work directly on `main` branch.** Always use a feature branch (e.g., `ivan`).

### Development Flow
```bash
# 1. Work on local feature branch
git checkout ivan
# ... make changes ...
git add <files>
git commit -m "message"

# 2. Push to origin feature branch
git push origin ivan

# 3. Merge to main on origin (via GitHub PR or command line)
git checkout main
git merge ivan
git push origin main

# 4. Sync local main
git checkout main
git pull origin main

# 5. Update feature branch from main
git checkout ivan
git merge main
```

### Branch Setup (First Time)
```bash
git checkout -b ivan
git push -u origin ivan
```

## Project Structure
```
csv2geo-api/
├── CLAUDE.md              # This file
├── README.md              # Public-facing overview
├── LICENSE                # MIT License
├── CONTRIBUTING.md        # Contribution guidelines
├── openapi.yaml           # OpenAPI 3.0 specification
├── docs/                  # Documentation site (Docusaurus)
│   ├── intro.md
│   ├── authentication.md
│   ├── endpoints/
│   └── errors.md
├── examples/              # Code examples
│   ├── curl/
│   ├── python/
│   ├── nodejs/
│   ├── php/
│   └── go/
└── sdks/                  # Client libraries (or links to separate repos)
```

## OpenAPI Specification
The `openapi.yaml` file is the single source of truth for the API. It:
- Defines all endpoints, parameters, and responses
- Generates interactive documentation (Swagger UI / Redoc)
- Can auto-generate client SDKs
- Is used by Postman, Insomnia, and other API tools

### Viewing the Spec
- **Swagger Editor**: https://editor.swagger.io (paste openapi.yaml)
- **Redoc**: Can be hosted as static HTML
- **Local**: Use VS Code OpenAPI extension

### Generating SDKs
```bash
# Using OpenAPI Generator
npx @openapitools/openapi-generator-cli generate \
  -i openapi.yaml \
  -g python \
  -o sdks/python
```

## Key Files
- `openapi.yaml` - API specification (edit this first when adding endpoints)
- `README.md` - What users see on GitHub
- `docs/index.html` - Scalar API documentation (auto-generated from openapi.yaml)
- `examples/` - Working code samples

## API Documentation (Scalar)

We use [Scalar](https://github.com/scalar/scalar) to render interactive API documentation from `openapi.yaml`.

### Local Development

```bash
# Start local server
npm run dev

# Open docs in browser
open http://localhost:3000/docs/
```

### How It Works
- `docs/index.html` loads Scalar from CDN
- Scalar reads `openapi.yaml` and generates interactive docs
- Users can try API endpoints directly in the browser
- Code examples auto-generated in 20+ languages

### Hosting Options
- **GitHub Pages** - Free, auto-deploys from main branch
- **Cloudflare Pages** - Free, fast CDN
- **Vercel** - Free tier available
- **Custom domain** - api.csv2geo.com/docs or docs.csv2geo.com

### Updating Documentation
1. Edit `openapi.yaml` (add endpoints, update schemas)
2. Refresh browser - Scalar auto-updates
3. Commit and push

## Related Projects
- [csv2geo](https://csv2geo.com) - Main geocoding application
- [overture-geocoder](../overture-geocoder) - Backend infrastructure

## API Base URL
- **Production**: `https://api.csv2geo.com/v1`
- **Documentation**: `https://docs.csv2geo.com` (planned)
