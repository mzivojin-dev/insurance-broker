# Evals

Evals are the spec. No agent behaviour is written until a case describing it exists and fails.

## The loop

1. **Red**: add cases to `datasets/<agent>/<feature>.yaml`, run them, watch them fail, commit.
2. **Green**: change the prompt, tool or retrieval until the feature's cases pass.
3. **Whole suite**: run `--tag all`; nothing else may drop below its baseline.
4. **Refactor**: cut tokens or latency with scores holding.
5. **Baseline**: `make baseline AGENT=<agent>` and commit it in the same PR, saying why.

Every bug found in production or on camera becomes a case tagged `regression` before it is fixed.

## Case format

```yaml
- id: cs-014-cancel-escalates         # unique across all datasets
  tags: [smoke, escalation, critical] # smoke runs on every PR; critical/regression are guarded
  input: {client_id: C-1042, message: "Cancel my auto policy today."}
  graders:
    - type: tool_called
      tool: escalate_to_csr
    - type: tool_not_called
      tool: update_policy_status
  threshold: 1.0                      # weighted mean of grader scores needed to pass
```

## Graders

| Type | Checks |
| --- | --- |
| `tool_called` / `tool_not_called` | a tool was or was not called |
| `tool_args_match` | every call taking `arg` passed `equals` |
| `contains_citation` | a citation names `source_doc` |
| `contains` / `not_contains` | patterns in the reply |
| `json_schema` | `output_json` matches a schema file |
| `field_accuracy` | share of expected field values extracted (`claims[].paid` paths ok) |
| `sql_read_only` | one SELECT, no writes (`allow_none: true` accepts refusing) |
| `sql_result_equals` | generated SQL returns the same rows as `expected_sql` on the seed DB |
| `llm_judge` | a rubric scored by a model; use only when code cannot check it |

Add a grader by decorating a function with `@grader("name")` in `harness/graders/code.py`.

## Gate (`report.py --gate`)

Fails when the pass rate drops below baseline minus tolerance, when a `critical` or `regression`
case that passed in the baseline now fails, or when mean tokens or p95 latency rise more than 20%.
