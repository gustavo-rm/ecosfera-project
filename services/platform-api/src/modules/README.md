# Domain modules

Every domain module created under this directory (e.g. `auth/`, `users/`,
`sessions/`) follows the layered convention defined in
[`docs/adr/0001-layered-module-convention.md`](../../../../docs/adr/0001-layered-module-convention.md):

```
<module>/
├── domain/
├── application/
├── infrastructure/
└── interface/
```

No module exists yet — this file only fixes the convention ahead of the first
real feature.
