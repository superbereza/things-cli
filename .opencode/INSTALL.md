# Installing for OpenCode

No marketplace — add to your `opencode.json` (global `~/.config/opencode/opencode.json` or project):

```json
{ "plugin": ["things@git+https://github.com/superbereza/things-cli.git"] }
```

Restart OpenCode. The plugin (`.opencode/plugins/things.js`) registers this repo's
`skills/` directory — no symlinks. Adapted from [obra/superpowers](https://github.com/obra/superpowers) (MIT); verify against your OpenCode version.
