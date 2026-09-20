---
name: supabase
description: >-
  Use this skill whenever the user wants to interact with Supabase databases,
  manage projects, run migrations, write edge functions, or generally interact
  with the Supabase CLI and MCP server.
---

# Supabase Skill

You are equipped with the Supabase CLI and the Supabase MCP Server.

## Capabilities

1. **Supabase CLI**: The `supabase` CLI is globally installed. You can use it to `supabase init`, `supabase start`, `supabase gen types typescript`, `supabase migration new`, etc.
2. **Supabase MCP Server**: The Supabase MCP Server is configured globally in `~/.gemini/config/mcp_config.json`. The tools it exposes are available to you. Use them to execute SQL queries, design database schemas, and manage projects.

## Instructions

- Use `supabase help` or specific command help like `supabase migration --help` if you need to know the syntax.
- For interacting directly with a hosted Supabase project, rely on the MCP tools which you should see injected in your context.
- Keep things simple and minimal (Ponytail mode applies here too). Use native Postgres features over app code when managing Supabase.
