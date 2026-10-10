# Coverage

<!-- GENERATED FILE. Do not edit by hand. Regenerate with `evalfloor report`. Every number here is computed from results/sweep.json and rulings.jsonl. -->

The denominator comes before the result. **Every task declared in an `eval.yaml` has exactly one row in the table at the bottom of this file**: it was swept and produced a floor, it is reachable but not yet swept, it failed when it was run, or there is a recorded reason it cannot be run.

> **No preregistration commit recorded.** This came from a smoke run, which is exempt from the ordering gate and is not a result.

| provenance | value |
|---|---|
| `inspect_ai` | 0.3.263 |
| `inspect_evals` | 0.24.0 |
| battery fingerprint | `b019ebb6ecee` |
| run fingerprint | `e498a3949683` |
| shuffle seed | 42 |
| sweep digest | `7981d9ebdb69df63` |

## Totals

| | count |
|---|---|
| tasks declared in `eval.yaml` files | 239 |
| reachable for the deterministic sweep | 58 |
| reachable, not counted, with a treatment | 13 |
| excluded, with a reason | 181 |
| attempted in this run | 45 |
| produced a scored floor | 45 |
| attempted but errored | 0 |
| flagged | 11 |

## Exclusion reasons

| reason | tasks | meaning |
|---|---|---|
| `sandbox_required` | 78 | the task or its scorer needs a container |
| `extra_dependency` | 49 | needs an optional dependency group that is not installed |
| `model_graded` | 27 | the scorer needs a grader model; not part of the deterministic arm |
| `network_required` | 17 | fetches from a URL or clones a repository at run time |
| `gated_dataset` | 7 | the Hugging Face dataset requires accepting terms or an access grant |
| `too_large` | 3 | the dataset exceeds the disk cap recorded in PREREGISTRATION.md |
| **reachable** | **58** | the deterministic sweep can run these |
| **declared total** | **239** | |

## Not counted

Reachable, and deliberately not swept. Each task has a `not_counted` row in `rulings.jsonl` that quotes the source line its treatment rests on, so the list is data rather than code.

| treatment | tasks | which |
|---|---|---|
| scores behaviour, not answer correctness | 6 | `agent_threat_bench_autonomy_hijack`, `agent_threat_bench_data_exfil`, `agent_threat_bench_memory_poison`, `air_bench`, `make_me_pay`, `stereoset` |
| needs solver state | 4 | `tau2_airline`, `tau2_banking`, `tau2_retail`, `tau2_telecom` |
| needs a judge | 3 | `agentharm`, `agentharm_benign`, `vqa_rad` |
| **not counted** | **13** | |

## Run failures

None. Every task attempted in this run produced a scored floor.

## Every task (239 rows)

| task | scorer | class | status | reason | detail |
|---|---|---|---|---|---|
| `inspect_evals/abstention_bench` | `abstention_bench_scorer(grader_model)` | `model_graded` | excluded | `extra_dependency` | eval.yaml: isolated: true (separate package) |
| `inspect_evals/agent_bench_os` | `agent_bench_os_default_scorer()` | `deterministic_custom` | excluded | `network_required` | external assets: git_clone |
| `inspect_evals/agent_threat_bench_autonomy_hijack` | `agent_threat_bench_scorer()` | `deterministic_custom` | not counted | `not_counted` | scores behaviour, not answer correctness |
| `inspect_evals/agent_threat_bench_data_exfil` | `agent_threat_bench_scorer()` | `deterministic_custom` | not counted | `not_counted` | scores behaviour, not answer correctness |
| `inspect_evals/agent_threat_bench_memory_poison` | `agent_threat_bench_scorer()` | `deterministic_custom` | not counted | `not_counted` | scores behaviour, not answer correctness |
| `inspect_evals/agentdojo` | `injection_task_scorer() if with_injections else user_task_scorer()` | `deterministic_custom` | excluded | `extra_dependency` | eval.yaml: dependency: agentdojo |
| `inspect_evals/agentharm` | `combined_scorer(grading_module, refusal_judge_model, semantic_judge_model)` | `deterministic_custom` | not counted | `not_counted` | needs a judge |
| `inspect_evals/agentharm_benign` | `combined_scorer(grading_module, refusal_judge_model, semantic_judge_model)` | `deterministic_custom` | not counted | `not_counted` | needs a judge |
| `inspect_evals/agentic_misalignment` | `[harmfulness_scorer(grader_model=grader_model)]` | `model_graded` | excluded | `extra_dependency` | eval.yaml: dependency: agentic_misalignment |
| `inspect_evals/agie_aqua_rat` | `expression_equivalence() if dataset_name in CLOZE_TASK else choice()` | `model_graded` | excluded | `model_graded` | expression_equivalence: custom, calls a grader model; choice: inspect_ai builtin, pure function of completion and target |
| `inspect_evals/agie_logiqa_en` | `expression_equivalence() if dataset_name in CLOZE_TASK else choice()` | `model_graded` | excluded | `model_graded` | expression_equivalence: custom, calls a grader model; choice: inspect_ai builtin, pure function of completion and target |
| `inspect_evals/agie_lsat_ar` | `expression_equivalence() if dataset_name in CLOZE_TASK else choice()` | `model_graded` | excluded | `model_graded` | expression_equivalence: custom, calls a grader model; choice: inspect_ai builtin, pure function of completion and target |
| `inspect_evals/agie_lsat_lr` | `expression_equivalence() if dataset_name in CLOZE_TASK else choice()` | `model_graded` | excluded | `model_graded` | expression_equivalence: custom, calls a grader model; choice: inspect_ai builtin, pure function of completion and target |
| `inspect_evals/agie_lsat_rc` | `expression_equivalence() if dataset_name in CLOZE_TASK else choice()` | `model_graded` | excluded | `model_graded` | expression_equivalence: custom, calls a grader model; choice: inspect_ai builtin, pure function of completion and target |
| `inspect_evals/agie_math` | `expression_equivalence() if dataset_name in CLOZE_TASK else choice()` | `model_graded` | excluded | `model_graded` | expression_equivalence: custom, calls a grader model; choice: inspect_ai builtin, pure function of completion and target |
| `inspect_evals/agie_sat_en` | `expression_equivalence() if dataset_name in CLOZE_TASK else choice()` | `model_graded` | excluded | `model_graded` | expression_equivalence: custom, calls a grader model; choice: inspect_ai builtin, pure function of completion and target |
| `inspect_evals/agie_sat_en_without_passage` | `expression_equivalence() if dataset_name in CLOZE_TASK else choice()` | `model_graded` | excluded | `model_graded` | expression_equivalence: custom, calls a grader model; choice: inspect_ai builtin, pure function of completion and target |
| `inspect_evals/agie_sat_math` | `expression_equivalence() if dataset_name in CLOZE_TASK else choice()` | `model_graded` | excluded | `model_graded` | expression_equivalence: custom, calls a grader model; choice: inspect_ai builtin, pure function of completion and target |
| `inspect_evals/aime2024` | `[aime_scorer()]` | `deterministic_custom` | swept, clean | `` |  |
| `inspect_evals/aime2025` | `[aime_scorer()]` | `deterministic_custom` | swept, clean | `` |  |
| `inspect_evals/aime2026` | `[aime_scorer()]` | `deterministic_custom` | swept, clean | `` |  |
| `inspect_evals/air_bench` | `air_bench_scorer()` | `deterministic_custom` | not counted | `not_counted` | scores behaviour, not answer correctness |
| `inspect_evals/anima` | `anima_scorer(dimensions=dims_by_name, revision=dataset_revision, grader_models=grader_models, grader_config=grader_config)` | `model_graded` | excluded | `extra_dependency` | eval.yaml: dependency: anima |
| `inspect_evals/ape_eval` | `ape_scorer()` | `deterministic_custom` | excluded | `network_required` | external assets: direct_url |
| `inspect_evals/apps` | `verify()` | `sandbox` | excluded | `sandbox_required` | verify: custom, executes in a sandbox |
| `inspect_evals/arc_challenge` | `choice()` | `deterministic` | swept, clean | `` |  |
| `inspect_evals/arc_easy` | `choice()` | `deterministic` | swept, clean | `` |  |
| `inspect_evals/assistant_bench_closed_book_one_shot` | `assistant_bench_scorer()` | `deterministic_custom` | excluded | `sandbox_required` | eval directory ships a Dockerfile or compose file |
| `inspect_evals/assistant_bench_closed_book_zero_shot` | `assistant_bench_scorer()` | `deterministic_custom` | excluded | `sandbox_required` | eval directory ships a Dockerfile or compose file |
| `inspect_evals/assistant_bench_web_browser` | `assistant_bench_scorer()` | `deterministic_custom` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/assistant_bench_web_search_one_shot` | `assistant_bench_scorer()` | `deterministic_custom` | excluded | `sandbox_required` | eval directory ships a Dockerfile or compose file |
| `inspect_evals/assistant_bench_web_search_zero_shot` | `assistant_bench_scorer()` | `deterministic_custom` | excluded | `sandbox_required` | eval directory ships a Dockerfile or compose file |
| `inspect_evals/b3` | `b3_scorer()` | `deterministic_custom` | excluded | `extra_dependency` | eval.yaml: dependency: b3 |
| `inspect_evals/bbeh` | `bbeh_scorer()` | `deterministic_custom` | swept, clean | `` |  |
| `inspect_evals/bbeh_mini` | `bbeh_scorer()` | `deterministic_custom` | swept, clean | `` |  |
| `inspect_evals/bbh` | `bbh_scorer()` | `deterministic_custom` | flagged | `` |  |
| `inspect_evals/bbq` | `choice()` | `deterministic` | swept, clean | `` |  |
| `inspect_evals/bfcl` | `bfcl_scorer()` | `deterministic_custom` | excluded | `extra_dependency` | eval.yaml: dependency: bfcl |
| `inspect_evals/bfcl_prereqs` | `_bfcl_prereqs_scorer()` | `deterministic_custom` | excluded | `extra_dependency` | eval.yaml: dependency: bfcl |
| `inspect_evals/bigcodebench` | `scorer or verify()` | `sandbox` | excluded | `sandbox_required` | verify: custom, executes in a sandbox |
| `inspect_evals/bold` | `[toxicity_scorer(), sentiment_scorer(), regard_scorer()]` | `deterministic_custom` | excluded | `extra_dependency` | eval.yaml: isolated: true (separate package) |
| `inspect_evals/boolq` | `pattern('\\A[\\W_]*(Yes\|No)[\\W_]*\\Z')` | `deterministic` | swept, clean | `` |  |
| `inspect_evals/browse_comp` | `browse_comp_scorer(scorer_model)` | `model_graded` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/chembench` | `chembench_scorer()` | `deterministic_custom` | swept, clean | `` |  |
| `inspect_evals/class_eval` | `class_eval_scorer()` | `sandbox` | excluded | `sandbox_required` | class_eval_scorer: custom, executes in a sandbox |
| `inspect_evals/coconot` | `[model_graded_qa(model=m, template=template, instructions=scorer_instructions, grade_pattern=grade_pattern) for m in grader_models]` | `model_graded` | excluded | `model_graded` | model_graded_qa: inspect_ai builtin grader |
| `inspect_evals/commonsense_qa` | `choice()` | `deterministic` | swept, clean | `` |  |
| `inspect_evals/compute_eval` | `correctness_scorer(cuda_version=cuda_version, benchmark_performance=benchmark_performance, benchmark_runs=benchmark_runs)` | `sandbox` | excluded | `sandbox_required` | correctness_scorer: custom, executes in a sandbox |
| `inspect_evals/core_bench` | `evaluate_task_questions()` | `sandbox` | excluded | `sandbox_required` | evaluate_task_questions: custom, executes in a sandbox |
| `inspect_evals/cti_realm_25` | `cti_realm_25_scorer()` | `deterministic_custom` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/cti_realm_25_minimal` | `cti_realm_25_scorer()` | `deterministic_custom` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/cti_realm_25_seeded` | `cti_realm_25_scorer()` | `deterministic_custom` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/cti_realm_50` | `cti_realm_50_scorer()` | `deterministic_custom` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/cve_bench` | `-` | `unknown` | excluded | `extra_dependency` | eval.yaml: isolated: true (separate package) |
| `inspect_evals/cybench` | `includes()` | `deterministic` | excluded | `extra_dependency` | eval.yaml: dependency: cybench |
| `inspect_evals/cybergym` | `cybergym_scorer()` | `sandbox` | excluded | `sandbox_required` | cybergym_scorer: custom, executes in a sandbox |
| `inspect_evals/cybermetric_10000` | `choice()` | `deterministic` | excluded | `network_required` | external assets: direct_url |
| `inspect_evals/cybermetric_2000` | `choice()` | `deterministic` | excluded | `network_required` | external assets: direct_url |
| `inspect_evals/cybermetric_500` | `choice()` | `deterministic` | excluded | `network_required` | external assets: direct_url |
| `inspect_evals/cybermetric_80` | `choice()` | `deterministic` | excluded | `network_required` | external assets: direct_url |
| `inspect_evals/cyse2_interpreter_abuse` | `model_graded_qa(template=PROMPT_JUDGE_RESPONSE, model=judge_llm)` | `model_graded` | excluded | `sandbox_required` | eval directory ships a Dockerfile or compose file |
| `inspect_evals/cyse2_prompt_injection` | `model_graded_qa(template=PROMPT_JUDGE_RESPONSE, model=judge_llm)` | `model_graded` | excluded | `sandbox_required` | eval directory ships a Dockerfile or compose file |
| `inspect_evals/cyse2_vulnerability_exploit` | `vul_exploit_scorer()` | `sandbox` | excluded | `sandbox_required` | vul_exploit_scorer: custom, executes in a sandbox |
| `inspect_evals/cyse3_visual_prompt_injection` | `model_graded_qa(template=PROMPT_JUDGE_RESPONSE, model=judge_llm)` | `model_graded` | excluded | `model_graded` | model_graded_qa: inspect_ai builtin grader |
| `inspect_evals/cyse4_autocomplete` | `security_scorer()` | `deterministic_custom` | excluded | `extra_dependency` | eval.yaml: dependency: cyberseceval_4 |
| `inspect_evals/cyse4_instruct` | `security_scorer()` | `deterministic_custom` | excluded | `extra_dependency` | eval.yaml: dependency: cyberseceval_4 |
| `inspect_evals/cyse4_malware_analysis` | `choice_with_jaccard()` | `deterministic_custom` | excluded | `extra_dependency` | eval.yaml: dependency: cyberseceval_4 |
| `inspect_evals/cyse4_mitre` | `mitre_scorer(expansion_llm=expansion_llm, judge_llm=judge_llm)` | `model_graded` | excluded | `extra_dependency` | eval.yaml: dependency: cyberseceval_4 |
| `inspect_evals/cyse4_mitre_frr` | `refusal_scorer()` | `deterministic_custom` | excluded | `extra_dependency` | eval.yaml: dependency: cyberseceval_4 |
| `inspect_evals/cyse4_multilingual_prompt_injection` | `prompt_injection_scorer(judge_llm=judge_llm)` | `model_graded` | excluded | `extra_dependency` | eval.yaml: dependency: cyberseceval_4 |
| `inspect_evals/cyse4_multiturn_phishing` | `phishing_scorer(judge_llm=judge_llm)` | `model_graded` | excluded | `extra_dependency` | eval.yaml: dependency: cyberseceval_4 |
| `inspect_evals/cyse4_threat_intelligence` | `choice_with_jaccard()` | `deterministic_custom` | excluded | `extra_dependency` | eval.yaml: dependency: cyberseceval_4 |
| `inspect_evals/docvqa` | `docvqa_scorer()` | `deterministic_custom` | excluded | `too_large` | 11.27 GiB on the Hub, cap is 1.00 GiB |
| `inspect_evals/drop` | `f1(extract_answer)` | `deterministic` | swept, clean | `` |  |
| `inspect_evals/ds1000` | `ds1000_scorer()` | `sandbox` | excluded | `sandbox_required` | ds1000_scorer: custom, executes in a sandbox |
| `inspect_evals/ds1000_sandbox_check` | `[sandbox_check_scorer(scorer, cases, expected_inventory=expected_inventory, exact_packages=exact_packages, extra_inventory_checks=extra_inventory_checks)]` | `deterministic_custom` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/fortress_adversarial` | `fortress_scorer_adversarial(grader_models)` | `model_graded` | excluded | `model_graded` | fortress_scorer_adversarial: custom, calls a grader model |
| `inspect_evals/fortress_benign` | `fortress_scorer_benign(grader_model)` | `model_graded` | excluded | `model_graded` | fortress_scorer_benign: custom, calls a grader model |
| `inspect_evals/frontier_cs` | `scorer or frontier_cs_scorer()` | `sandbox` | excluded | `sandbox_required` | frontier_cs_scorer: custom, executes in a sandbox |
| `inspect_evals/frontier_cs_algorithmic` | `scorer or frontier_cs_scorer()` | `sandbox` | excluded | `sandbox_required` | frontier_cs_scorer: custom, executes in a sandbox |
| `inspect_evals/frontier_cs_research` | `scorer or frontier_cs_scorer()` | `sandbox` | excluded | `sandbox_required` | frontier_cs_scorer: custom, executes in a sandbox |
| `inspect_evals/frontierscience` | `frontierscience_scorer(model=grader_model)` | `model_graded` | excluded | `model_graded` | frontierscience_scorer: custom, calls a grader model |
| `inspect_evals/gaia` | `gaia_scorer() if split == 'validation' else None` | `deterministic_custom` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/gaia_level1` | `gaia_scorer() if split == 'validation' else None` | `deterministic_custom` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/gaia_level2` | `gaia_scorer() if split == 'validation' else None` | `deterministic_custom` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/gaia_level3` | `gaia_scorer() if split == 'validation' else None` | `deterministic_custom` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/gdm_classifier_evasion` | `scorer` | `sandbox` | excluded | `sandbox_required` | scorer: custom, executes in a sandbox |
| `inspect_evals/gdm_cover_your_tracks` | `scorer` | `sandbox` | excluded | `sandbox_required` | scorer: custom, executes in a sandbox |
| `inspect_evals/gdm_in_house_ctf` | `check_flag()` | `sandbox` | excluded | `sandbox_required` | check_flag: custom, executes in a sandbox |
| `inspect_evals/gdm_intercode_ctf` | `includes()` | `deterministic` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/gdm_oversight_pattern` | `scorer` | `sandbox` | excluded | `sandbox_required` | scorer: custom, executes in a sandbox |
| `inspect_evals/gdm_self_reasoning_approved_directories` | `_success_scorer()` | `deterministic_custom` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/gdm_self_reasoning_calculator_improvement` | `_success_scorer()` | `deterministic_custom` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/gdm_self_reasoning_context_length_mod_instrumental_only` | `_success_scorer()` | `deterministic_custom` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/gdm_self_reasoning_context_length_mod_irreversibility_only` | `_success_scorer()` | `deterministic_custom` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/gdm_self_reasoning_database_tool` | `_success_scorer()` | `deterministic_custom` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/gdm_self_reasoning_latency_calculator` | `_success_scorer()` | `deterministic_custom` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/gdm_self_reasoning_max_messages_calculator` | `_success_scorer()` | `deterministic_custom` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/gdm_self_reasoning_max_tokens` | `_success_scorer()` | `deterministic_custom` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/gdm_self_reasoning_oversight_frequency` | `_success_scorer()` | `deterministic_custom` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/gdm_self_reasoning_read_logs` | `_success_scorer()` | `deterministic_custom` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/gdm_self_reasoning_turn_off_filters` | `_success_scorer()` | `deterministic_custom` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/gdm_sp01_e2e` | `scorer_module.milestone_scorer()` | `deterministic_custom` | excluded | `extra_dependency` | eval.yaml: dependency: gdm_self_proliferation |
| `inspect_evals/gdm_sp02_e2e` | `scorer_module.milestone_scorer()` | `deterministic_custom` | excluded | `extra_dependency` | eval.yaml: dependency: gdm_self_proliferation |
| `inspect_evals/gdm_sp03_e2e` | `scorer_module.milestone_scorer()` | `deterministic_custom` | excluded | `extra_dependency` | eval.yaml: dependency: gdm_self_proliferation |
| `inspect_evals/gdm_sp04_e2e` | `scorer_module.milestone_scorer()` | `deterministic_custom` | excluded | `extra_dependency` | eval.yaml: dependency: gdm_self_proliferation |
| `inspect_evals/gdm_sp05_e2e` | `scorer_module.milestone_scorer()` | `deterministic_custom` | excluded | `extra_dependency` | eval.yaml: dependency: gdm_self_proliferation |
| `inspect_evals/gdm_sp07_e2e` | `scorer_module.milestone_scorer()` | `deterministic_custom` | excluded | `extra_dependency` | eval.yaml: dependency: gdm_self_proliferation |
| `inspect_evals/gdm_sp08_e2e` | `scorer_module.milestone_scorer()` | `deterministic_custom` | excluded | `extra_dependency` | eval.yaml: dependency: gdm_self_proliferation |
| `inspect_evals/gdm_sp09_e2e` | `scorer_module.milestone_scorer()` | `deterministic_custom` | excluded | `extra_dependency` | eval.yaml: dependency: gdm_self_proliferation |
| `inspect_evals/gdm_sp10_e2e` | `scorer_module.milestone_scorer()` | `deterministic_custom` | excluded | `extra_dependency` | eval.yaml: dependency: gdm_self_proliferation |
| `inspect_evals/gdm_sp12_e2e` | `scorer_module.milestone_scorer()` | `deterministic_custom` | excluded | `extra_dependency` | eval.yaml: dependency: gdm_self_proliferation |
| `inspect_evals/gdm_strategic_rule_breaking` | `scorer` | `sandbox` | excluded | `sandbox_required` | scorer: custom, executes in a sandbox |
| `inspect_evals/gdpval` | `scorer` | `sandbox` | excluded | `sandbox_required` | scorer: custom, executes in a sandbox |
| `inspect_evals/gpqa_diamond` | `choice()` | `deterministic` | excluded | `network_required` | external assets: direct_url |
| `inspect_evals/gsm8k` | `match(numeric=True)` | `deterministic` | swept, clean | `` |  |
| `inspect_evals/healthbench` | `healthbench_scorer(judge_model=judge_model, judge_max_tokens=judge_max_tokens, judge_temperature=judge_temperature, judge_system_message=judge_system_message, bootstrap_samples=bootstrap_samples, include_subset_scores=include_subset_scores, length_adjustment_center=length_adjustment_center, length_adjustment_penalty_per_500_chars=length_adjustment_penalty_per_500_chars)` | `model_graded` | excluded | `extra_dependency` | eval.yaml: dependency: healthbench |
| `inspect_evals/healthbench_consensus` | `healthbench_scorer(judge_model=judge_model, judge_max_tokens=judge_max_tokens, judge_temperature=judge_temperature, judge_system_message=judge_system_message, bootstrap_samples=bootstrap_samples, include_subset_scores=include_subset_scores, length_adjustment_center=length_adjustment_center, length_adjustment_penalty_per_500_chars=length_adjustment_penalty_per_500_chars)` | `model_graded` | excluded | `extra_dependency` | eval.yaml: dependency: healthbench |
| `inspect_evals/healthbench_hard` | `healthbench_scorer(judge_model=judge_model, judge_max_tokens=judge_max_tokens, judge_temperature=judge_temperature, judge_system_message=judge_system_message, bootstrap_samples=bootstrap_samples, include_subset_scores=include_subset_scores, length_adjustment_center=length_adjustment_center, length_adjustment_penalty_per_500_chars=length_adjustment_penalty_per_500_chars)` | `model_graded` | excluded | `extra_dependency` | eval.yaml: dependency: healthbench |
| `inspect_evals/healthbench_meta_eval` | `healthbench_scorer(judge_model=judge_model, judge_max_tokens=judge_max_tokens, judge_temperature=judge_temperature, judge_system_message=judge_system_message, bootstrap_samples=bootstrap_samples, include_subset_scores=include_subset_scores, length_adjustment_center=length_adjustment_center, length_adjustment_penalty_per_500_chars=length_adjustment_penalty_per_500_chars)` | `model_graded` | excluded | `extra_dependency` | eval.yaml: dependency: healthbench |
| `inspect_evals/hellaswag` | `choice()` | `deterministic` | swept, clean | `` |  |
| `inspect_evals/hle` | `scorers_from_spec(scorer)` | `deterministic_custom` | excluded | `gated_dataset` | gated on the Hub: cais/hle, skylenage-ai/HLE-Verified, cais/hle-rolling |
| `inspect_evals/humaneval` | `scorer or verify()` | `sandbox` | excluded | `sandbox_required` | verify: custom, executes in a sandbox |
| `inspect_evals/ifeval` | `instruction_following()` | `deterministic_custom` | excluded | `extra_dependency` | eval.yaml: dependency: ifeval |
| `inspect_evals/ifevalcode` | `ifevalcode_scorer()` | `deterministic_custom` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/infinite_bench_code_debug` | `scorer` | `sandbox` | excluded | `sandbox_required` | scorer: custom, executes in a sandbox |
| `inspect_evals/infinite_bench_code_run` | `scorer` | `sandbox` | excluded | `sandbox_required` | scorer: custom, executes in a sandbox |
| `inspect_evals/infinite_bench_kv_retrieval` | `scorer` | `sandbox` | excluded | `sandbox_required` | scorer: custom, executes in a sandbox |
| `inspect_evals/infinite_bench_longbook_choice_eng` | `scorer` | `sandbox` | excluded | `sandbox_required` | scorer: custom, executes in a sandbox |
| `inspect_evals/infinite_bench_longdialogue_qa_eng` | `scorer` | `sandbox` | excluded | `sandbox_required` | scorer: custom, executes in a sandbox |
| `inspect_evals/infinite_bench_math_calc` | `scorer` | `sandbox` | excluded | `sandbox_required` | scorer: custom, executes in a sandbox |
| `inspect_evals/infinite_bench_math_find` | `scorer` | `sandbox` | excluded | `sandbox_required` | scorer: custom, executes in a sandbox |
| `inspect_evals/infinite_bench_number_string` | `scorer` | `sandbox` | excluded | `sandbox_required` | scorer: custom, executes in a sandbox |
| `inspect_evals/infinite_bench_passkey` | `scorer` | `sandbox` | excluded | `sandbox_required` | scorer: custom, executes in a sandbox |
| `inspect_evals/instrumentaleval` | `instrumentaleval_scorer(grader_model=get_model(grader_model, config=GenerateConfig(temperature=grader_temperature)))` | `model_graded` | excluded | `model_graded` | instrumentaleval_scorer: custom, calls a grader model; get_model: custom, definition not found in this eval package; GenerateConfig: custom, |
| `inspect_evals/ipi_coding_agent` | `ipi_scorer()` | `sandbox` | excluded | `sandbox_required` | ipi_scorer: custom, executes in a sandbox |
| `inspect_evals/kernelbench` | `[kernelbench_scorer(num_correct_trials=num_correct_trials, num_perf_trials=num_perf_trials, measure_performance=measure_performance, timing_method=timing_method, verbose=verbose, build_dir=build_dir, device=device, backend=backend, precision=precision)]` | `sandbox` | excluded | `sandbox_required` | kernelbench_scorer: custom, executes in a sandbox |
| `inspect_evals/kernelbench_sandbox_check` | `[sandbox_check_scorer(scorer, cases, expected_inventory=expected_inventory, exact_packages=exact_packages, extra_inventory_checks=extra_inventory_checks)]` | `deterministic_custom` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/lab_bench_cloning_scenarios` | `precision_choice(no_answer=UNCERTAIN_ANSWER_CHOICE)` | `deterministic_custom` | swept, clean | `` |  |
| `inspect_evals/lab_bench_dbqa` | `precision_choice(no_answer=UNCERTAIN_ANSWER_CHOICE)` | `deterministic_custom` | flagged | `` |  |
| `inspect_evals/lab_bench_figqa` | `precision_choice(no_answer=UNCERTAIN_ANSWER_CHOICE)` | `deterministic_custom` | swept, clean | `` |  |
| `inspect_evals/lab_bench_litqa` | `precision_choice(no_answer=UNCERTAIN_ANSWER_CHOICE)` | `deterministic_custom` | flagged | `` |  |
| `inspect_evals/lab_bench_protocolqa` | `precision_choice(no_answer=UNCERTAIN_ANSWER_CHOICE)` | `deterministic_custom` | swept, clean | `` |  |
| `inspect_evals/lab_bench_seqqa` | `precision_choice(no_answer=UNCERTAIN_ANSWER_CHOICE)` | `deterministic_custom` | flagged | `` |  |
| `inspect_evals/lab_bench_suppqa` | `precision_choice(no_answer=UNCERTAIN_ANSWER_CHOICE)` | `deterministic_custom` | swept, clean | `` |  |
| `inspect_evals/lab_bench_tableqa` | `precision_choice(no_answer=UNCERTAIN_ANSWER_CHOICE)` | `deterministic_custom` | flagged | `` |  |
| `inspect_evals/lingoly` | `exact_match_lingoly()` | `deterministic_custom` | excluded | `gated_dataset` | gated on the Hub: ambean/lingOly, jkhouja/LingOly-TOO |
| `inspect_evals/lingoly_too` | `exact_match_lingoly_too()` | `deterministic_custom` | excluded | `gated_dataset` | gated on the Hub: ambean/lingOly, jkhouja/LingOly-TOO |
| `inspect_evals/livebench` | `[decide_scorer()]` | `deterministic_custom` | excluded | `extra_dependency` | eval.yaml: isolated: true (separate package) |
| `inspect_evals/livecodebench_pro` | `custom_scorer or livecodebench_pro_scorer()` | `sandbox` | excluded | `sandbox_required` | livecodebench_pro_scorer: custom, executes in a sandbox |
| `inspect_evals/macbench` | `macbench_scorer()` | `deterministic_custom` | swept, clean | `` |  |
| `inspect_evals/make_me_pay` | `make_me_pay_scorer()` | `deterministic_custom` | not counted | `not_counted` | scores behaviour, not answer correctness |
| `inspect_evals/makemesay` | `makemesay_scorer()` | `deterministic_custom` | excluded | `extra_dependency` | eval.yaml: dependency: makemesay |
| `inspect_evals/mask` | `[accuracy_and_honesty(honesty_at_n=honesty_at_n, binary_judge_model=binary_judge_model, numeric_judge_model=numeric_judge_model, numeric_tol=numeric_tol, no_belief_handling=NoBeliefConsistencyHandling(no_belief_handling), judge_config=judge_config)]` | `model_graded` | excluded | `model_graded` | accuracy_and_honesty: custom, calls a grader model; NoBeliefConsistencyHandling: custom, definition not found in this eval package |
| `inspect_evals/math` | `[expression_equivalance(model=grader_model), expression_exact_match(), expression_exact_match_sympy()]` | `deterministic_custom` | excluded | `extra_dependency` | eval.yaml: dependency: math |
| `inspect_evals/mathvista` | `mathvista_scorer()` | `deterministic_custom` | excluded | `too_large` | 1.63 GiB on the Hub, cap is 1.00 GiB |
| `inspect_evals/mbpp` | `verify()` | `sandbox` | excluded | `sandbox_required` | verify: custom, executes in a sandbox |
| `inspect_evals/medqa` | `choice()` | `deterministic` | excluded | `extra_dependency` | eval.yaml: dependency: medqa |
| `inspect_evals/mgsm` | `match(numeric=True)` | `deterministic` | excluded | `network_required` | external assets: direct_url |
| `inspect_evals/mind2web` | `[mind2web_scorer()]` | `deterministic_custom` | excluded | `extra_dependency` | eval.yaml: dependency: mind2web |
| `inspect_evals/mind2web_sc` | `guard_agent_scorer()` | `deterministic_custom` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/mle_bench` | `scorer or mle_bench_scorer()` | `sandbox` | excluded | `sandbox_required` | mle_bench_scorer: custom, executes in a sandbox |
| `inspect_evals/mle_bench_full` | `scorer or mle_bench_scorer()` | `sandbox` | excluded | `sandbox_required` | mle_bench_scorer: custom, executes in a sandbox |
| `inspect_evals/mle_bench_lite` | `scorer or mle_bench_scorer()` | `sandbox` | excluded | `sandbox_required` | mle_bench_scorer: custom, executes in a sandbox |
| `inspect_evals/mlrc_bench` | `mlrc_scorer()` | `sandbox` | excluded | `sandbox_required` | mlrc_scorer: custom, executes in a sandbox |
| `inspect_evals/mmiu` | `mmiu_scorer()` | `deterministic_custom` | excluded | `network_required` | external assets: direct_url |
| `inspect_evals/mmlu_0_shot` | `choice()` | `deterministic` | swept, clean | `` |  |
| `inspect_evals/mmlu_5_shot` | `choice()` | `deterministic` | swept, clean | `` |  |
| `inspect_evals/mmlu_pro` | `choice()` | `deterministic` | flagged | `` |  |
| `inspect_evals/mmmu_multiple_choice` | `choice()` | `deterministic` | excluded | `too_large` | 3.40 GiB on the Hub, cap is 1.00 GiB |
| `inspect_evals/mmmu_open` | `model_graded_fact()` | `model_graded` | excluded | `model_graded` | model_graded_fact: inspect_ai builtin grader |
| `inspect_evals/moru` | `moru_scorer(dimensions=dims_by_name, grader_models=grader_models, grader_config=grader_config)` | `model_graded` | excluded | `model_graded` | moru_scorer: custom, calls a grader model |
| `inspect_evals/musr` | `choice()` | `deterministic` | flagged | `` |  |
| `inspect_evals/niah` | `custom_model_graded_qa_with_history_scorer(include_history=return_metadata_variable_as_history)` | `model_graded` | excluded | `extra_dependency` | eval.yaml: dependency: niah |
| `inspect_evals/novelty_bench` | `novelty_bench_scorer(equivalence_threshold=equivalence_threshold, quality_model=quality_model, quality_model_device=select_device(quality_model_device), partition_model_device=select_device(partition_model_device))` | `deterministic_custom` | excluded | `extra_dependency` | eval.yaml: isolated: true (separate package) |
| `inspect_evals/onet_m6` | `choice()` | `deterministic` | swept, clean | `` |  |
| `inspect_evals/osworld` | `osworld_scorer()` | `sandbox` | excluded | `sandbox_required` | osworld_scorer: custom, executes in a sandbox |
| `inspect_evals/osworld_small` | `osworld_scorer()` | `sandbox` | excluded | `sandbox_required` | osworld_scorer: custom, executes in a sandbox |
| `inspect_evals/paperbench` | `blacklist_url_monitor()` | `deterministic_custom` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/paws` | `pattern('\\A\\W*\\b(Yes\|No)\\b\\W*\\Z')` | `deterministic` | swept, clean | `` |  |
| `inspect_evals/persistbench_beneficial_memory` | `persistbench_judge()` | `model_graded` | excluded | `model_graded` | persistbench_judge: custom, calls a grader model |
| `inspect_evals/persistbench_cross_domain` | `persistbench_judge()` | `model_graded` | excluded | `model_graded` | persistbench_judge: custom, calls a grader model |
| `inspect_evals/persistbench_sycophancy` | `persistbench_judge()` | `model_graded` | excluded | `model_graded` | persistbench_judge: custom, calls a grader model |
| `inspect_evals/personality_BFI` | `any_choice()` | `deterministic_custom` | excluded | `extra_dependency` | eval.yaml: dependency: personality |
| `inspect_evals/personality_TRAIT` | `any_choice()` | `deterministic_custom` | excluded | `extra_dependency` | eval.yaml: dependency: personality |
| `inspect_evals/piqa` | `choice()` | `deterministic` | excluded | `network_required` | external assets: direct_url |
| `inspect_evals/pre_flight` | `choice()` | `deterministic` | swept, clean | `` |  |
| `inspect_evals/pubmedqa` | `choice()` | `deterministic` | flagged | `` |  |
| `inspect_evals/race_h` | `choice()` | `deterministic` | swept, clean | `` |  |
| `inspect_evals/sad_facts_human_defaults` | `lenient_mcq_choice()` | `deterministic_custom` | excluded | `network_required` | external assets: direct_url |
| `inspect_evals/sad_facts_llms` | `lenient_mcq_choice()` | `deterministic_custom` | excluded | `network_required` | external assets: direct_url |
| `inspect_evals/sad_influence` | `lenient_mcq_choice()` | `deterministic_custom` | excluded | `network_required` | external assets: direct_url |
| `inspect_evals/sad_stages_full` | `lenient_mcq_choice()` | `deterministic_custom` | excluded | `network_required` | external assets: direct_url |
| `inspect_evals/sad_stages_oversight` | `lenient_mcq_choice()` | `deterministic_custom` | excluded | `network_required` | external assets: direct_url |
| `inspect_evals/scbench` | `scorer or scbench_scorer()` | `sandbox` | excluded | `sandbox_required` | scbench_scorer: custom, executes in a sandbox |
| `inspect_evals/scicode` | `verify(timeout)` | `deterministic_custom` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/sciknoweval` | `sciknoweval_scorer(scorer_config)` | `deterministic_custom` | excluded | `extra_dependency` | eval.yaml: dependency: sciknoweval |
| `inspect_evals/sec_qa_v1` | `choice()` | `deterministic` | swept, clean | `` |  |
| `inspect_evals/sec_qa_v1_5_shot` | `choice()` | `deterministic` | swept, clean | `` |  |
| `inspect_evals/sec_qa_v2` | `choice()` | `deterministic` | swept, clean | `` |  |
| `inspect_evals/sec_qa_v2_5_shot` | `choice()` | `deterministic` | swept, clean | `` |  |
| `inspect_evals/sevenllm_mcq_en` | `choice()` | `deterministic` | excluded | `extra_dependency` | eval.yaml: dependency: sevenllm |
| `inspect_evals/sevenllm_mcq_zh` | `choice()` | `deterministic` | excluded | `extra_dependency` | eval.yaml: dependency: sevenllm |
| `inspect_evals/sevenllm_qa_en` | `[rouge_l_scorer(is_zh=False), semantic_similarity_scorer()]` | `deterministic_custom` | excluded | `extra_dependency` | eval.yaml: dependency: sevenllm |
| `inspect_evals/sevenllm_qa_zh` | `[rouge_l_scorer(is_zh=True), semantic_similarity_scorer()]` | `deterministic_custom` | excluded | `extra_dependency` | eval.yaml: dependency: sevenllm |
| `inspect_evals/simpleqa` | `_resolve_scorer(scorer, SIMPLEQA_GRADER_TEMPLATE, grade_parse)` | `deterministic_custom` | excluded | `network_required` | external assets: direct_url |
| `inspect_evals/simpleqa_verified` | `_resolve_scorer(scorer, SIMPLEQA_VERIFIED_GRADER_TEMPLATE, grade_parse)` | `deterministic_custom` | excluded | `network_required` | external assets: direct_url |
| `inspect_evals/sosbench` | `llm_judge_scorer(template=LLM_JUDGE_TEMPLATE)` | `model_graded` | excluded | `model_graded` | llm_judge_scorer: custom, calls a grader model |
| `inspect_evals/squad` | `[f1(), exact()]` | `deterministic` | swept, clean | `` |  |
| `inspect_evals/stereoset` | `[multiple_choice_scorer(), stereoset_scorer()]` | `deterministic_custom` | not counted | `not_counted` | scores behaviour, not answer correctness |
| `inspect_evals/strong_reject` | `strong_reject_scorer(judge_llm)` | `model_graded` | excluded | `model_graded` | strong_reject_scorer: custom, calls a grader model |
| `inspect_evals/swe_bench` | `scorer or swe_bench_scorer()` | `sandbox` | excluded | `sandbox_required` | swe_bench_scorer: custom, executes in a sandbox |
| `inspect_evals/swe_bench_verified_mini` | `scorer or swe_bench_scorer()` | `sandbox` | excluded | `sandbox_required` | swe_bench_scorer: custom, executes in a sandbox |
| `inspect_evals/swe_lancer` | `scorers + [debug_artifact_exporter(base_path=debug_export_path)]` | `sandbox` | excluded | `sandbox_required` | debug_artifact_exporter: custom, executes in a sandbox |
| `inspect_evals/sycophancy` | `sycophancy_scorer(scorer_model=scorer_model)` | `model_graded` | excluded | `model_graded` | sycophancy_scorer: custom, calls a grader model |
| `inspect_evals/tac` | `tac_scorer()` | `deterministic_custom` | excluded | `gated_dataset` | gated on the Hub: CompassioninMachineLearning/tac |
| `inspect_evals/tac_welfare` | `tac_scorer()` | `deterministic_custom` | excluded | `gated_dataset` | gated on the Hub: CompassioninMachineLearning/tac |
| `inspect_evals/tau2_airline` | `airline_scorer()` | `deterministic_custom` | not counted | `not_counted` | needs solver state |
| `inspect_evals/tau2_banking` | `banking_scorer()` | `deterministic_custom` | not counted | `not_counted` | needs solver state |
| `inspect_evals/tau2_retail` | `retail_scorer()` | `deterministic_custom` | not counted | `not_counted` | needs solver state |
| `inspect_evals/tau2_telecom` | `telecom_scorer()` | `deterministic_custom` | not counted | `not_counted` | needs solver state |
| `inspect_evals/theagentcompany` | `get_scorer_for_task(task_name, scoring_mode=scoring_mode)` | `deterministic_custom` | excluded | `extra_dependency` | eval.yaml: dependency: theagentcompany |
| `inspect_evals/threecb` | `best_elicitation_per_challenge()` | `deterministic_custom` | excluded | `sandbox_required` | eval directory ships a Dockerfile or compose file |
| `inspect_evals/truthfulqa` | `choice()` | `deterministic` | flagged | `` |  |
| `inspect_evals/uccb` | `model_graded_qa(template=UCCB_GRADING_TEMPLATE, model=scorer_model)` | `model_graded` | excluded | `model_graded` | model_graded_qa: inspect_ai builtin grader |
| `inspect_evals/usaco` | `verify()` | `deterministic_custom` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/vimgolf_single_turn` | `vimgolf_scorer()` | `deterministic_custom` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/vqa_rad` | `vqa_rad_graded_scorer()` | `deterministic_custom` | not counted | `not_counted` | needs a judge |
| `inspect_evals/vstar_bench_attribute_recognition` | `choice()` | `deterministic` | flagged | `` |  |
| `inspect_evals/vstar_bench_spatial_relationship_reasoning` | `choice()` | `deterministic` | swept, clean | `` |  |
| `inspect_evals/winogrande` | `choice()` | `deterministic` | swept, clean | `` |  |
| `inspect_evals/wmdp_bio` | `choice()` | `deterministic` | swept, clean | `` |  |
| `inspect_evals/wmdp_chem` | `choice()` | `deterministic` | swept, clean | `` |  |
| `inspect_evals/wmdp_cyber` | `choice()` | `deterministic` | flagged | `` |  |
| `inspect_evals/worldsense` | `pattern_with_metadata('^\\(?\\s*(1\|2\|3\|TRUE\|FALSE\|IMPOSSIBLE\|POSSIBLE)\\s*\\)?')` | `deterministic_custom` | excluded | `extra_dependency` | eval.yaml: dependency: worldsense |
| `inspect_evals/writingbench` | `multi_scorer_wrapper(judge_model=judge_model)` | `model_graded` | excluded | `model_graded` | multi_scorer_wrapper: custom, calls a grader model |
| `inspect_evals/xstest` | `model_graded_qa(model=scorer_model, template=scorer_template, instructions=scorer_instructions)` | `model_graded` | excluded | `model_graded` | model_graded_qa: inspect_ai builtin grader |
| `inspect_evals/zerobench` | `zerobench_scorer()` | `deterministic_custom` | excluded | `gated_dataset` | gated on the Hub: jonathan-roberts1/zerobench |
| `inspect_evals/zerobench_subquestions` | `zerobench_scorer()` | `deterministic_custom` | excluded | `gated_dataset` | gated on the Hub: jonathan-roberts1/zerobench |

239 rows for 239 declared tasks. Every declared task is accounted for; none is silently dropped.
