# Task inventory

<!-- GENERATED FILE. Do not edit by hand. Regenerate with `evalfloor inventory`. -->

Built by static analysis of the installed `inspect_evals` 0.24.0 package against `inspect_ai` 0.3.263. No dataset was downloaded to produce this file.

## Totals

| | count |
|---|---|
| tasks declared in `eval.yaml` files | 239 |
| of those, registered in `_registry.py` | 239 |
| reachable for the deterministic sweep | 58 |
| excluded | 181 |

## Scorer class

| class | tasks |
|---|---|
| `deterministic_custom` | 114 |
| `deterministic` | 42 |
| `model_graded` | 41 |
| `sandbox` | 41 |
| `unknown` | 1 |

## Exclusion reasons

| reason | tasks |
|---|---|
| `sandbox_required` | 78 |
| `extra_dependency` | 49 |
| `model_graded` | 27 |
| `network_required` | 17 |
| `gated_dataset` | 7 |
| `too_large` | 3 |

## Reachable tasks with simple deterministic scorers

| task | scorer | samples | hub size | group |
|---|---|---|---|---|
| `inspect_evals/vstar_bench_spatial_relationship_reasoning` | `choice()` | 76 | 362.6 MiB | Multimodal |
| `inspect_evals/sec_qa_v2` | `choice()` | 100 | 0.1 MiB | Cybersecurity |
| `inspect_evals/sec_qa_v2_5_shot` | `choice()` | 100 | 0.1 MiB | Cybersecurity |
| `inspect_evals/sec_qa_v1` | `choice()` | 110 | 0.1 MiB | Cybersecurity |
| `inspect_evals/sec_qa_v1_5_shot` | `choice()` | 110 | 0.1 MiB | Cybersecurity |
| `inspect_evals/vstar_bench_attribute_recognition` | `choice()` | 115 | 362.6 MiB | Multimodal |
| `inspect_evals/musr` | `choice()` | 250 | 6.8 MiB | Reasoning |
| `inspect_evals/pre_flight` | `choice()` | 300 | 0.1 MiB | Knowledge |
| `inspect_evals/onet_m6` | `choice()` | 397 | 1.6 MiB | Knowledge |
| `inspect_evals/wmdp_chem` | `choice()` | 408 | 1.3 MiB | Safeguards |
| `inspect_evals/pubmedqa` | `choice()` | 500 | 286.6 MiB | Knowledge |
| `inspect_evals/truthfulqa` | `choice()` | 817 | 0.5 MiB | Knowledge |
| `inspect_evals/arc_challenge` | `choice()` | 1172 | 1.2 MiB | Reasoning |
| `inspect_evals/commonsense_qa` | `choice()` | 1221 | 1.5 MiB | Knowledge |
| `inspect_evals/winogrande` | `choice()` | 1267 | 4.4 MiB | Reasoning |
| `inspect_evals/wmdp_bio` | `choice()` | 1273 | 1.3 MiB | Safeguards |
| `inspect_evals/gsm8k` | `match(numeric=True)` | 1319 | 5.6 MiB | Mathematics |
| `inspect_evals/wmdp_cyber` | `choice()` | 1987 | 1.3 MiB | Safeguards |
| `inspect_evals/arc_easy` | `choice()` | 2376 | 1.2 MiB | Reasoning |
| `inspect_evals/boolq` | `pattern('\\A[\\W_]*(Yes\|No)[\\W_]*\\Z')` | 3270 | 4.7 MiB | Reasoning |
| `inspect_evals/race_h` | `choice()` | 3498 | 79.2 MiB | Reasoning |
| `inspect_evals/paws` | `pattern('\\A\\W*\\b(Yes\|No)\\b\\W*\\Z')` | 8000 | 123.3 MiB | Reasoning |
| `inspect_evals/drop` | `f1(extract_answer)` | 9535 | 11.1 MiB | Reasoning |
| `inspect_evals/hellaswag` | `choice()` | 10042 | 35.1 MiB | Reasoning |
| `inspect_evals/squad` | `[f1(), exact()]` | 11873 | 16.9 MiB | Reasoning |
| `inspect_evals/mmlu_pro` | `choice()` | 12032 | 4.0 MiB | Knowledge |
| `inspect_evals/mmlu_0_shot` | `choice()` | 13937 | 257.5 MiB | Knowledge |
| `inspect_evals/mmlu_5_shot` | `choice()` | 14015 | 257.5 MiB | Knowledge |
| `inspect_evals/bbq` | `choice()` | 58492 | 48.6 MiB | Bias |

## First sweep: the preregistered 20

Selection rule: simple deterministic scorer, reachable, ranked by dataset size ascending with ties broken by name, at most 2 tasks per eval directory, first 20. Generated, not typed.

| # | task | scorer | samples | hub size |
|---|---|---|---|---|
| 1 | `inspect_evals/vstar_bench_spatial_relationship_reasoning` | `choice()` | 76 | 362.6 MiB |
| 2 | `inspect_evals/sec_qa_v2` | `choice()` | 100 | 0.1 MiB |
| 3 | `inspect_evals/sec_qa_v2_5_shot` | `choice()` | 100 | 0.1 MiB |
| 4 | `inspect_evals/vstar_bench_attribute_recognition` | `choice()` | 115 | 362.6 MiB |
| 5 | `inspect_evals/musr` | `choice()` | 250 | 6.8 MiB |
| 6 | `inspect_evals/pre_flight` | `choice()` | 300 | 0.1 MiB |
| 7 | `inspect_evals/onet_m6` | `choice()` | 397 | 1.6 MiB |
| 8 | `inspect_evals/wmdp_chem` | `choice()` | 408 | 1.3 MiB |
| 9 | `inspect_evals/pubmedqa` | `choice()` | 500 | 286.6 MiB |
| 10 | `inspect_evals/truthfulqa` | `choice()` | 817 | 0.5 MiB |
| 11 | `inspect_evals/arc_challenge` | `choice()` | 1172 | 1.2 MiB |
| 12 | `inspect_evals/commonsense_qa` | `choice()` | 1221 | 1.5 MiB |
| 13 | `inspect_evals/winogrande` | `choice()` | 1267 | 4.4 MiB |
| 14 | `inspect_evals/wmdp_bio` | `choice()` | 1273 | 1.3 MiB |
| 15 | `inspect_evals/gsm8k` | `match(numeric=True)` | 1319 | 5.6 MiB |
| 16 | `inspect_evals/arc_easy` | `choice()` | 2376 | 1.2 MiB |
| 17 | `inspect_evals/boolq` | `pattern('\\A[\\W_]*(Yes\|No)[\\W_]*\\Z')` | 3270 | 4.7 MiB |
| 18 | `inspect_evals/race_h` | `choice()` | 3498 | 79.2 MiB |
| 19 | `inspect_evals/paws` | `pattern('\\A\\W*\\b(Yes\|No)\\b\\W*\\Z')` | 8000 | 123.3 MiB |
| 20 | `inspect_evals/drop` | `f1(extract_answer)` | 9535 | 11.1 MiB |

Reserves, in order, replacing any of the twenty that fails at run time: `inspect_evals/hellaswag`, `inspect_evals/squad`, `inspect_evals/mmlu_pro`, `inspect_evals/mmlu_0_shot`, `inspect_evals/mmlu_5_shot`.

## Every task

| task | scorer expression | class | samples | reachable | reason |
|---|---|---|---|---|---|
| `inspect_evals/abstention_bench` | `abstention_bench_scorer(grader_model)` | `model_graded` | 39277 | no | extra_dependency |
| `inspect_evals/agent_bench_os` | `agent_bench_os_default_scorer()` | `deterministic_custom` | 119 | no | network_required |
| `inspect_evals/agent_threat_bench_autonomy_hijack` | `agent_threat_bench_scorer()` | `deterministic_custom` | 6 | yes |  |
| `inspect_evals/agent_threat_bench_data_exfil` | `agent_threat_bench_scorer()` | `deterministic_custom` | 8 | yes |  |
| `inspect_evals/agent_threat_bench_memory_poison` | `agent_threat_bench_scorer()` | `deterministic_custom` | 10 | yes |  |
| `inspect_evals/agentdojo` | `injection_task_scorer() if with_injections else user_task_scorer()` | `deterministic_custom` | 1014 | no | extra_dependency |
| `inspect_evals/agentharm` | `combined_scorer(grading_module, refusal_judge_model, semantic_judge_model)` | `deterministic_custom` | 176 | yes |  |
| `inspect_evals/agentharm_benign` | `combined_scorer(grading_module, refusal_judge_model, semantic_judge_model)` | `deterministic_custom` | 176 | yes |  |
| `inspect_evals/agentic_misalignment` | `[harmfulness_scorer(grader_model=grader_model)]` | `model_graded` | 1 | no | extra_dependency |
| `inspect_evals/agie_aqua_rat` | `expression_equivalence() if dataset_name in CLOZE_TASK else choice()` | `model_graded` | 254 | no | model_graded |
| `inspect_evals/agie_logiqa_en` | `expression_equivalence() if dataset_name in CLOZE_TASK else choice()` | `model_graded` | 651 | no | model_graded |
| `inspect_evals/agie_lsat_ar` | `expression_equivalence() if dataset_name in CLOZE_TASK else choice()` | `model_graded` | 230 | no | model_graded |
| `inspect_evals/agie_lsat_lr` | `expression_equivalence() if dataset_name in CLOZE_TASK else choice()` | `model_graded` | 510 | no | model_graded |
| `inspect_evals/agie_lsat_rc` | `expression_equivalence() if dataset_name in CLOZE_TASK else choice()` | `model_graded` | 269 | no | model_graded |
| `inspect_evals/agie_math` | `expression_equivalence() if dataset_name in CLOZE_TASK else choice()` | `model_graded` | 1000 | no | model_graded |
| `inspect_evals/agie_sat_en` | `expression_equivalence() if dataset_name in CLOZE_TASK else choice()` | `model_graded` | 206 | no | model_graded |
| `inspect_evals/agie_sat_en_without_passage` | `expression_equivalence() if dataset_name in CLOZE_TASK else choice()` | `model_graded` | 206 | no | model_graded |
| `inspect_evals/agie_sat_math` | `expression_equivalence() if dataset_name in CLOZE_TASK else choice()` | `model_graded` | 220 | no | model_graded |
| `inspect_evals/aime2024` | `[aime_scorer()]` | `deterministic_custom` | 30 | yes |  |
| `inspect_evals/aime2025` | `[aime_scorer()]` | `deterministic_custom` | 30 | yes |  |
| `inspect_evals/aime2026` | `[aime_scorer()]` | `deterministic_custom` | 30 | yes |  |
| `inspect_evals/air_bench` | `air_bench_scorer()` | `deterministic_custom` | 5694 | yes |  |
| `inspect_evals/anima` | `anima_scorer(dimensions=dims_by_name, revision=dataset_revision, grader_models=grader_models, grader_config=grader_config)` | `model_graded` | 115 | no | extra_dependency |
| `inspect_evals/ape_eval` | `ape_scorer()` | `deterministic_custom` | 600 | no | network_required |
| `inspect_evals/apps` | `verify()` | `sandbox` | 3000 | no | sandbox_required |
| `inspect_evals/arc_challenge` | `choice()` | `deterministic` | 1172 | yes |  |
| `inspect_evals/arc_easy` | `choice()` | `deterministic` | 2376 | yes |  |
| `inspect_evals/assistant_bench_closed_book_one_shot` | `assistant_bench_scorer()` | `deterministic_custom` | 33 | no | sandbox_required |
| `inspect_evals/assistant_bench_closed_book_zero_shot` | `assistant_bench_scorer()` | `deterministic_custom` | 33 | no | sandbox_required |
| `inspect_evals/assistant_bench_web_browser` | `assistant_bench_scorer()` | `deterministic_custom` | 33 | no | sandbox_required |
| `inspect_evals/assistant_bench_web_search_one_shot` | `assistant_bench_scorer()` | `deterministic_custom` | 33 | no | sandbox_required |
| `inspect_evals/assistant_bench_web_search_zero_shot` | `assistant_bench_scorer()` | `deterministic_custom` | 33 | no | sandbox_required |
| `inspect_evals/b3` | `b3_scorer()` | `deterministic_custom` | 630 | no | extra_dependency |
| `inspect_evals/bbeh` | `bbeh_scorer()` | `deterministic_custom` | 4519 | yes |  |
| `inspect_evals/bbeh_mini` | `bbeh_scorer()` | `deterministic_custom` | 460 | yes |  |
| `inspect_evals/bbh` | `bbh_scorer()` | `deterministic_custom` | 6509 | yes |  |
| `inspect_evals/bbq` | `choice()` | `deterministic` | 58492 | yes |  |
| `inspect_evals/bfcl` | `bfcl_scorer()` | `deterministic_custom` | 4981 | no | extra_dependency |
| `inspect_evals/bfcl_prereqs` | `_bfcl_prereqs_scorer()` | `deterministic_custom` | 111 | no | extra_dependency |
| `inspect_evals/bigcodebench` | `scorer or verify()` | `sandbox` | 1140 | no | sandbox_required |
| `inspect_evals/bold` | `[toxicity_scorer(), sentiment_scorer(), regard_scorer()]` | `deterministic_custom` | 7200 | no | extra_dependency |
| `inspect_evals/boolq` | `pattern('\\A[\\W_]*(Yes\|No)[\\W_]*\\Z')` | `deterministic` | 3270 | yes |  |
| `inspect_evals/browse_comp` | `browse_comp_scorer(scorer_model)` | `model_graded` | 1266 | no | sandbox_required |
| `inspect_evals/chembench` | `chembench_scorer()` | `deterministic_custom` | 2786 | yes |  |
| `inspect_evals/class_eval` | `class_eval_scorer()` | `sandbox` | 100 | no | sandbox_required |
| `inspect_evals/coconot` | `[model_graded_qa(model=m, template=template, instructions=scorer_instructions, grade_pattern=grade_pattern) for m in grader_models]` | `model_graded` | 1001 | no | model_graded |
| `inspect_evals/commonsense_qa` | `choice()` | `deterministic` | 1221 | yes |  |
| `inspect_evals/compute_eval` | `correctness_scorer(cuda_version=cuda_version, benchmark_performance=benchmark_performance, benchmark_runs=benchmark_runs)` | `sandbox` | 406 | no | sandbox_required |
| `inspect_evals/core_bench` | `evaluate_task_questions()` | `sandbox` | 45 | no | sandbox_required |
| `inspect_evals/cti_realm_25` | `cti_realm_25_scorer()` | `deterministic_custom` | 25 | no | sandbox_required |
| `inspect_evals/cti_realm_25_minimal` | `cti_realm_25_scorer()` | `deterministic_custom` | 25 | no | sandbox_required |
| `inspect_evals/cti_realm_25_seeded` | `cti_realm_25_scorer()` | `deterministic_custom` | 25 | no | sandbox_required |
| `inspect_evals/cti_realm_50` | `cti_realm_50_scorer()` | `deterministic_custom` | 50 | no | sandbox_required |
| `inspect_evals/cve_bench` | `-` | `unknown` | 40 | no | extra_dependency |
| `inspect_evals/cybench` | `includes()` | `deterministic` | 39 | no | extra_dependency |
| `inspect_evals/cybergym` | `cybergym_scorer()` | `sandbox` | 6028 | no | sandbox_required |
| `inspect_evals/cybermetric_10000` | `choice()` | `deterministic` | 10000 | no | network_required |
| `inspect_evals/cybermetric_2000` | `choice()` | `deterministic` | 2000 | no | network_required |
| `inspect_evals/cybermetric_500` | `choice()` | `deterministic` | 500 | no | network_required |
| `inspect_evals/cybermetric_80` | `choice()` | `deterministic` | 80 | no | network_required |
| `inspect_evals/cyse2_interpreter_abuse` | `model_graded_qa(template=PROMPT_JUDGE_RESPONSE, model=judge_llm)` | `model_graded` | 489 | no | sandbox_required |
| `inspect_evals/cyse2_prompt_injection` | `model_graded_qa(template=PROMPT_JUDGE_RESPONSE, model=judge_llm)` | `model_graded` | 250 | no | sandbox_required |
| `inspect_evals/cyse2_vulnerability_exploit` | `vul_exploit_scorer()` | `sandbox` | 585 | no | sandbox_required |
| `inspect_evals/cyse3_visual_prompt_injection` | `model_graded_qa(template=PROMPT_JUDGE_RESPONSE, model=judge_llm)` | `model_graded` | 1000 | no | model_graded |
| `inspect_evals/cyse4_autocomplete` | `security_scorer()` | `deterministic_custom` | 1916 | no | extra_dependency |
| `inspect_evals/cyse4_instruct` | `security_scorer()` | `deterministic_custom` | 1916 | no | extra_dependency |
| `inspect_evals/cyse4_malware_analysis` | `choice_with_jaccard()` | `deterministic_custom` | 609 | no | extra_dependency |
| `inspect_evals/cyse4_mitre` | `mitre_scorer(expansion_llm=expansion_llm, judge_llm=judge_llm)` | `model_graded` | 1000 | no | extra_dependency |
| `inspect_evals/cyse4_mitre_frr` | `refusal_scorer()` | `deterministic_custom` | 750 | no | extra_dependency |
| `inspect_evals/cyse4_multilingual_prompt_injection` | `prompt_injection_scorer(judge_llm=judge_llm)` | `model_graded` | 1004 | no | extra_dependency |
| `inspect_evals/cyse4_multiturn_phishing` | `phishing_scorer(judge_llm=judge_llm)` | `model_graded` | 100 | no | extra_dependency |
| `inspect_evals/cyse4_threat_intelligence` | `choice_with_jaccard()` | `deterministic_custom` | 588 | no | extra_dependency |
| `inspect_evals/docvqa` | `docvqa_scorer()` | `deterministic_custom` | 5349 | no | too_large |
| `inspect_evals/drop` | `f1(extract_answer)` | `deterministic` | 9535 | yes |  |
| `inspect_evals/ds1000` | `ds1000_scorer()` | `sandbox` | 1000 | no | sandbox_required |
| `inspect_evals/ds1000_sandbox_check` | `[sandbox_check_scorer(scorer, cases, expected_inventory=expected_inventory, exact_packages=exact_packages, extra_inventory_checks=extra_inventory_checks)]` | `deterministic_custom` | 4 | no | sandbox_required |
| `inspect_evals/fortress_adversarial` | `fortress_scorer_adversarial(grader_models)` | `model_graded` | 500 | no | model_graded |
| `inspect_evals/fortress_benign` | `fortress_scorer_benign(grader_model)` | `model_graded` | 500 | no | model_graded |
| `inspect_evals/frontier_cs` | `scorer or frontier_cs_scorer()` | `sandbox` | 238 | no | sandbox_required |
| `inspect_evals/frontier_cs_algorithmic` | `scorer or frontier_cs_scorer()` | `sandbox` | 172 | no | sandbox_required |
| `inspect_evals/frontier_cs_research` | `scorer or frontier_cs_scorer()` | `sandbox` | 66 | no | sandbox_required |
| `inspect_evals/frontierscience` | `frontierscience_scorer(model=grader_model)` | `model_graded` | 160 | no | model_graded |
| `inspect_evals/gaia` | `gaia_scorer() if split == 'validation' else None` | `deterministic_custom` | 165 | no | sandbox_required |
| `inspect_evals/gaia_level1` | `gaia_scorer() if split == 'validation' else None` | `deterministic_custom` | 53 | no | sandbox_required |
| `inspect_evals/gaia_level2` | `gaia_scorer() if split == 'validation' else None` | `deterministic_custom` | 86 | no | sandbox_required |
| `inspect_evals/gaia_level3` | `gaia_scorer() if split == 'validation' else None` | `deterministic_custom` | 26 | no | sandbox_required |
| `inspect_evals/gdm_classifier_evasion` | `scorer` | `sandbox` | 9 | no | sandbox_required |
| `inspect_evals/gdm_cover_your_tracks` | `scorer` | `sandbox` | 2 | no | sandbox_required |
| `inspect_evals/gdm_in_house_ctf` | `check_flag()` | `sandbox` | 13 | no | sandbox_required |
| `inspect_evals/gdm_intercode_ctf` | `includes()` | `deterministic` | 78 | no | sandbox_required |
| `inspect_evals/gdm_oversight_pattern` | `scorer` | `sandbox` | 2 | no | sandbox_required |
| `inspect_evals/gdm_self_reasoning_approved_directories` | `_success_scorer()` | `deterministic_custom` | 2 | no | sandbox_required |
| `inspect_evals/gdm_self_reasoning_calculator_improvement` | `_success_scorer()` | `deterministic_custom` | 2 | no | sandbox_required |
| `inspect_evals/gdm_self_reasoning_context_length_mod_instrumental_only` | `_success_scorer()` | `deterministic_custom` | 2 | no | sandbox_required |
| `inspect_evals/gdm_self_reasoning_context_length_mod_irreversibility_only` | `_success_scorer()` | `deterministic_custom` | 2 | no | sandbox_required |
| `inspect_evals/gdm_self_reasoning_database_tool` | `_success_scorer()` | `deterministic_custom` | 2 | no | sandbox_required |
| `inspect_evals/gdm_self_reasoning_latency_calculator` | `_success_scorer()` | `deterministic_custom` | 2 | no | sandbox_required |
| `inspect_evals/gdm_self_reasoning_max_messages_calculator` | `_success_scorer()` | `deterministic_custom` | 2 | no | sandbox_required |
| `inspect_evals/gdm_self_reasoning_max_tokens` | `_success_scorer()` | `deterministic_custom` | 2 | no | sandbox_required |
| `inspect_evals/gdm_self_reasoning_oversight_frequency` | `_success_scorer()` | `deterministic_custom` | 2 | no | sandbox_required |
| `inspect_evals/gdm_self_reasoning_read_logs` | `_success_scorer()` | `deterministic_custom` | 2 | no | sandbox_required |
| `inspect_evals/gdm_self_reasoning_turn_off_filters` | `_success_scorer()` | `deterministic_custom` | 2 | no | sandbox_required |
| `inspect_evals/gdm_sp01_e2e` | `scorer_module.milestone_scorer()` | `deterministic_custom` | 1 | no | extra_dependency |
| `inspect_evals/gdm_sp02_e2e` | `scorer_module.milestone_scorer()` | `deterministic_custom` | 1 | no | extra_dependency |
| `inspect_evals/gdm_sp03_e2e` | `scorer_module.milestone_scorer()` | `deterministic_custom` | 1 | no | extra_dependency |
| `inspect_evals/gdm_sp04_e2e` | `scorer_module.milestone_scorer()` | `deterministic_custom` | 1 | no | extra_dependency |
| `inspect_evals/gdm_sp05_e2e` | `scorer_module.milestone_scorer()` | `deterministic_custom` | 1 | no | extra_dependency |
| `inspect_evals/gdm_sp07_e2e` | `scorer_module.milestone_scorer()` | `deterministic_custom` | 1 | no | extra_dependency |
| `inspect_evals/gdm_sp08_e2e` | `scorer_module.milestone_scorer()` | `deterministic_custom` | 1 | no | extra_dependency |
| `inspect_evals/gdm_sp09_e2e` | `scorer_module.milestone_scorer()` | `deterministic_custom` | 1 | no | extra_dependency |
| `inspect_evals/gdm_sp10_e2e` | `scorer_module.milestone_scorer()` | `deterministic_custom` | 1 | no | extra_dependency |
| `inspect_evals/gdm_sp12_e2e` | `scorer_module.milestone_scorer()` | `deterministic_custom` | 1 | no | extra_dependency |
| `inspect_evals/gdm_strategic_rule_breaking` | `scorer` | `sandbox` | 1 | no | sandbox_required |
| `inspect_evals/gdpval` | `scorer` | `sandbox` | 220 | no | sandbox_required |
| `inspect_evals/gpqa_diamond` | `choice()` | `deterministic` | 198 | no | network_required |
| `inspect_evals/gsm8k` | `match(numeric=True)` | `deterministic` | 1319 | yes |  |
| `inspect_evals/healthbench` | `healthbench_scorer(judge_model=judge_model, judge_max_tokens=judge_max_tokens, judge_temperature=judge_temperature, judge_system_message=judge_system_message, bootstrap_samples=bootstrap_samples, include_subset_scores=include_subset_scores, length_adjustment_center=length_adjustment_center, length_adjustment_penalty_per_500_chars=length_adjustment_penalty_per_500_chars)` | `model_graded` | 5000 | no | extra_dependency |
| `inspect_evals/healthbench_consensus` | `healthbench_scorer(judge_model=judge_model, judge_max_tokens=judge_max_tokens, judge_temperature=judge_temperature, judge_system_message=judge_system_message, bootstrap_samples=bootstrap_samples, include_subset_scores=include_subset_scores, length_adjustment_center=length_adjustment_center, length_adjustment_penalty_per_500_chars=length_adjustment_penalty_per_500_chars)` | `model_graded` | 3671 | no | extra_dependency |
| `inspect_evals/healthbench_hard` | `healthbench_scorer(judge_model=judge_model, judge_max_tokens=judge_max_tokens, judge_temperature=judge_temperature, judge_system_message=judge_system_message, bootstrap_samples=bootstrap_samples, include_subset_scores=include_subset_scores, length_adjustment_center=length_adjustment_center, length_adjustment_penalty_per_500_chars=length_adjustment_penalty_per_500_chars)` | `model_graded` | 1000 | no | extra_dependency |
| `inspect_evals/healthbench_meta_eval` | `healthbench_scorer(judge_model=judge_model, judge_max_tokens=judge_max_tokens, judge_temperature=judge_temperature, judge_system_message=judge_system_message, bootstrap_samples=bootstrap_samples, include_subset_scores=include_subset_scores, length_adjustment_center=length_adjustment_center, length_adjustment_penalty_per_500_chars=length_adjustment_penalty_per_500_chars)` | `model_graded` | 29511 | no | extra_dependency |
| `inspect_evals/hellaswag` | `choice()` | `deterministic` | 10042 | yes |  |
| `inspect_evals/hle` | `scorers_from_spec(scorer)` | `deterministic_custom` | 668 | no | gated_dataset |
| `inspect_evals/humaneval` | `scorer or verify()` | `sandbox` | 164 | no | sandbox_required |
| `inspect_evals/ifeval` | `instruction_following()` | `deterministic_custom` | 541 | no | extra_dependency |
| `inspect_evals/ifevalcode` | `ifevalcode_scorer()` | `deterministic_custom` | 810 | no | sandbox_required |
| `inspect_evals/infinite_bench_code_debug` | `scorer` | `sandbox` | 394 | no | sandbox_required |
| `inspect_evals/infinite_bench_code_run` | `scorer` | `sandbox` | 400 | no | sandbox_required |
| `inspect_evals/infinite_bench_kv_retrieval` | `scorer` | `sandbox` | 500 | no | sandbox_required |
| `inspect_evals/infinite_bench_longbook_choice_eng` | `scorer` | `sandbox` | 229 | no | sandbox_required |
| `inspect_evals/infinite_bench_longdialogue_qa_eng` | `scorer` | `sandbox` | 200 | no | sandbox_required |
| `inspect_evals/infinite_bench_math_calc` | `scorer` | `sandbox` | 50 | no | sandbox_required |
| `inspect_evals/infinite_bench_math_find` | `scorer` | `sandbox` | 350 | no | sandbox_required |
| `inspect_evals/infinite_bench_number_string` | `scorer` | `sandbox` | 590 | no | sandbox_required |
| `inspect_evals/infinite_bench_passkey` | `scorer` | `sandbox` | 590 | no | sandbox_required |
| `inspect_evals/instrumentaleval` | `instrumentaleval_scorer(grader_model=get_model(grader_model, config=GenerateConfig(temperature=grader_temperature)))` | `model_graded` | 76 | no | model_graded |
| `inspect_evals/ipi_coding_agent` | `ipi_scorer()` | `sandbox` | 45 | no | sandbox_required |
| `inspect_evals/kernelbench` | `[kernelbench_scorer(num_correct_trials=num_correct_trials, num_perf_trials=num_perf_trials, measure_performance=measure_performance, timing_method=timing_method, verbose=verbose, build_dir=build_dir, device=device, backend=backend, precision=precision)]` | `sandbox` | 250 | no | sandbox_required |
| `inspect_evals/kernelbench_sandbox_check` | `[sandbox_check_scorer(scorer, cases, expected_inventory=expected_inventory, exact_packages=exact_packages, extra_inventory_checks=extra_inventory_checks)]` | `deterministic_custom` | 3 | no | sandbox_required |
| `inspect_evals/lab_bench_cloning_scenarios` | `precision_choice(no_answer=UNCERTAIN_ANSWER_CHOICE)` | `deterministic_custom` | 33 | yes |  |
| `inspect_evals/lab_bench_dbqa` | `precision_choice(no_answer=UNCERTAIN_ANSWER_CHOICE)` | `deterministic_custom` | 520 | yes |  |
| `inspect_evals/lab_bench_figqa` | `precision_choice(no_answer=UNCERTAIN_ANSWER_CHOICE)` | `deterministic_custom` | 181 | yes |  |
| `inspect_evals/lab_bench_litqa` | `precision_choice(no_answer=UNCERTAIN_ANSWER_CHOICE)` | `deterministic_custom` | 199 | yes |  |
| `inspect_evals/lab_bench_protocolqa` | `precision_choice(no_answer=UNCERTAIN_ANSWER_CHOICE)` | `deterministic_custom` | 108 | yes |  |
| `inspect_evals/lab_bench_seqqa` | `precision_choice(no_answer=UNCERTAIN_ANSWER_CHOICE)` | `deterministic_custom` | 600 | yes |  |
| `inspect_evals/lab_bench_suppqa` | `precision_choice(no_answer=UNCERTAIN_ANSWER_CHOICE)` | `deterministic_custom` | 82 | yes |  |
| `inspect_evals/lab_bench_tableqa` | `precision_choice(no_answer=UNCERTAIN_ANSWER_CHOICE)` | `deterministic_custom` | 244 | yes |  |
| `inspect_evals/lingoly` | `exact_match_lingoly()` | `deterministic_custom` | 408 | no | gated_dataset |
| `inspect_evals/lingoly_too` | `exact_match_lingoly_too()` | `deterministic_custom` | 1203 | no | gated_dataset |
| `inspect_evals/livebench` | `[decide_scorer()]` | `deterministic_custom` | 910 | no | extra_dependency |
| `inspect_evals/livecodebench_pro` | `custom_scorer or livecodebench_pro_scorer()` | `sandbox` | 706 | no | sandbox_required |
| `inspect_evals/macbench` | `macbench_scorer()` | `deterministic_custom` | 1153 | yes |  |
| `inspect_evals/make_me_pay` | `make_me_pay_scorer()` | `deterministic_custom` | 20 | yes |  |
| `inspect_evals/makemesay` | `makemesay_scorer()` | `deterministic_custom` | 189 | no | extra_dependency |
| `inspect_evals/mask` | `[accuracy_and_honesty(honesty_at_n=honesty_at_n, binary_judge_model=binary_judge_model, numeric_judge_model=numeric_judge_model, numeric_tol=numeric_tol, no_belief_handling=NoBeliefConsistencyHandling(no_belief_handling), judge_config=judge_config)]` | `model_graded` | 1000 | no | model_graded |
| `inspect_evals/math` | `[expression_equivalance(model=grader_model), expression_exact_match(), expression_exact_match_sympy()]` | `deterministic_custom` | 12500 | no | extra_dependency |
| `inspect_evals/mathvista` | `mathvista_scorer()` | `deterministic_custom` | 1000 | no | too_large |
| `inspect_evals/mbpp` | `verify()` | `sandbox` | 257 | no | sandbox_required |
| `inspect_evals/medqa` | `choice()` | `deterministic` | 1273 | no | extra_dependency |
| `inspect_evals/mgsm` | `match(numeric=True)` | `deterministic` | 2750 | no | network_required |
| `inspect_evals/mind2web` | `[mind2web_scorer()]` | `deterministic_custom` | 7775 | no | extra_dependency |
| `inspect_evals/mind2web_sc` | `guard_agent_scorer()` | `deterministic_custom` | 200 | no | sandbox_required |
| `inspect_evals/mle_bench` | `scorer or mle_bench_scorer()` | `sandbox` | 1 | no | sandbox_required |
| `inspect_evals/mle_bench_full` | `scorer or mle_bench_scorer()` | `sandbox` | 75 | no | sandbox_required |
| `inspect_evals/mle_bench_lite` | `scorer or mle_bench_scorer()` | `sandbox` | 22 | no | sandbox_required |
| `inspect_evals/mlrc_bench` | `mlrc_scorer()` | `sandbox` | 7 | no | sandbox_required |
| `inspect_evals/mmiu` | `mmiu_scorer()` | `deterministic_custom` | 11698 | no | network_required |
| `inspect_evals/mmlu_0_shot` | `choice()` | `deterministic` | 13937 | yes |  |
| `inspect_evals/mmlu_5_shot` | `choice()` | `deterministic` | 14015 | yes |  |
| `inspect_evals/mmlu_pro` | `choice()` | `deterministic` | 12032 | yes |  |
| `inspect_evals/mmmu_multiple_choice` | `choice()` | `deterministic` | 847 | no | too_large |
| `inspect_evals/mmmu_open` | `model_graded_fact()` | `model_graded` | 53 | no | model_graded |
| `inspect_evals/moru` | `moru_scorer(dimensions=dims_by_name, grader_models=grader_models, grader_config=grader_config)` | `model_graded` | 201 | no | model_graded |
| `inspect_evals/musr` | `choice()` | `deterministic` | 250 | yes |  |
| `inspect_evals/niah` | `custom_model_graded_qa_with_history_scorer(include_history=return_metadata_variable_as_history)` | `model_graded` | 225 | no | extra_dependency |
| `inspect_evals/novelty_bench` | `novelty_bench_scorer(equivalence_threshold=equivalence_threshold, quality_model=quality_model, quality_model_device=select_device(quality_model_device), partition_model_device=select_device(partition_model_device))` | `deterministic_custom` | 1100 | no | extra_dependency |
| `inspect_evals/onet_m6` | `choice()` | `deterministic` | 397 | yes |  |
| `inspect_evals/osworld` | `osworld_scorer()` | `sandbox` | 369 | no | sandbox_required |
| `inspect_evals/osworld_small` | `osworld_scorer()` | `sandbox` | 39 | no | sandbox_required |
| `inspect_evals/paperbench` | `blacklist_url_monitor()` | `deterministic_custom` | 23 | no | sandbox_required |
| `inspect_evals/paws` | `pattern('\\A\\W*\\b(Yes\|No)\\b\\W*\\Z')` | `deterministic` | 8000 | yes |  |
| `inspect_evals/persistbench_beneficial_memory` | `persistbench_judge()` | `model_graded` | 100 | no | model_graded |
| `inspect_evals/persistbench_cross_domain` | `persistbench_judge()` | `model_graded` | 200 | no | model_graded |
| `inspect_evals/persistbench_sycophancy` | `persistbench_judge()` | `model_graded` | 200 | no | model_graded |
| `inspect_evals/personality_BFI` | `any_choice()` | `deterministic_custom` | 44 | no | extra_dependency |
| `inspect_evals/personality_TRAIT` | `any_choice()` | `deterministic_custom` | 8000 | no | extra_dependency |
| `inspect_evals/piqa` | `choice()` | `deterministic` | 1838 | no | network_required |
| `inspect_evals/pre_flight` | `choice()` | `deterministic` | 300 | yes |  |
| `inspect_evals/pubmedqa` | `choice()` | `deterministic` | 500 | yes |  |
| `inspect_evals/race_h` | `choice()` | `deterministic` | 3498 | yes |  |
| `inspect_evals/sad_facts_human_defaults` | `lenient_mcq_choice()` | `deterministic_custom` | 1200 | no | network_required |
| `inspect_evals/sad_facts_llms` | `lenient_mcq_choice()` | `deterministic_custom` | 249 | no | network_required |
| `inspect_evals/sad_influence` | `lenient_mcq_choice()` | `deterministic_custom` | 255 | no | network_required |
| `inspect_evals/sad_stages_full` | `lenient_mcq_choice()` | `deterministic_custom` | 800 | no | network_required |
| `inspect_evals/sad_stages_oversight` | `lenient_mcq_choice()` | `deterministic_custom` | 400 | no | network_required |
| `inspect_evals/scbench` | `scorer or scbench_scorer()` | `sandbox` | 30 | no | sandbox_required |
| `inspect_evals/scicode` | `verify(timeout)` | `deterministic_custom` | 65 | no | sandbox_required |
| `inspect_evals/sciknoweval` | `sciknoweval_scorer(scorer_config)` | `deterministic_custom` | 69736 | no | extra_dependency |
| `inspect_evals/sec_qa_v1` | `choice()` | `deterministic` | 110 | yes |  |
| `inspect_evals/sec_qa_v1_5_shot` | `choice()` | `deterministic` | 110 | yes |  |
| `inspect_evals/sec_qa_v2` | `choice()` | `deterministic` | 100 | yes |  |
| `inspect_evals/sec_qa_v2_5_shot` | `choice()` | `deterministic` | 100 | yes |  |
| `inspect_evals/sevenllm_mcq_en` | `choice()` | `deterministic` | 50 | no | extra_dependency |
| `inspect_evals/sevenllm_mcq_zh` | `choice()` | `deterministic` | 50 | no | extra_dependency |
| `inspect_evals/sevenllm_qa_en` | `[rouge_l_scorer(is_zh=False), semantic_similarity_scorer()]` | `deterministic_custom` | 600 | no | extra_dependency |
| `inspect_evals/sevenllm_qa_zh` | `[rouge_l_scorer(is_zh=True), semantic_similarity_scorer()]` | `deterministic_custom` | 600 | no | extra_dependency |
| `inspect_evals/simpleqa` | `_resolve_scorer(scorer, SIMPLEQA_GRADER_TEMPLATE, grade_parse)` | `deterministic_custom` | 4326 | no | network_required |
| `inspect_evals/simpleqa_verified` | `_resolve_scorer(scorer, SIMPLEQA_VERIFIED_GRADER_TEMPLATE, grade_parse)` | `deterministic_custom` | 1000 | no | network_required |
| `inspect_evals/sosbench` | `llm_judge_scorer(template=LLM_JUDGE_TEMPLATE)` | `model_graded` | 3000 | no | model_graded |
| `inspect_evals/squad` | `[f1(), exact()]` | `deterministic` | 11873 | yes |  |
| `inspect_evals/stereoset` | `[multiple_choice_scorer(), stereoset_scorer()]` | `deterministic_custom` | 2123 | yes |  |
| `inspect_evals/strong_reject` | `strong_reject_scorer(judge_llm)` | `model_graded` | 324 | no | model_graded |
| `inspect_evals/swe_bench` | `scorer or swe_bench_scorer()` | `sandbox` | 500 | no | sandbox_required |
| `inspect_evals/swe_bench_verified_mini` | `scorer or swe_bench_scorer()` | `sandbox` | 50 | no | sandbox_required |
| `inspect_evals/swe_lancer` | `scorers + [debug_artifact_exporter(base_path=debug_export_path)]` | `sandbox` | 460 | no | sandbox_required |
| `inspect_evals/sycophancy` | `sycophancy_scorer(scorer_model=scorer_model)` | `model_graded` | 4882 | no | model_graded |
| `inspect_evals/tac` | `tac_scorer()` | `deterministic_custom` | 52 | no | gated_dataset |
| `inspect_evals/tac_welfare` | `tac_scorer()` | `deterministic_custom` | 52 | no | gated_dataset |
| `inspect_evals/tau2_airline` | `airline_scorer()` | `deterministic_custom` | 50 | yes |  |
| `inspect_evals/tau2_banking` | `banking_scorer()` | `deterministic_custom` | 97 | yes |  |
| `inspect_evals/tau2_retail` | `retail_scorer()` | `deterministic_custom` | 114 | yes |  |
| `inspect_evals/tau2_telecom` | `telecom_scorer()` | `deterministic_custom` | 114 | yes |  |
| `inspect_evals/theagentcompany` | `get_scorer_for_task(task_name, scoring_mode=scoring_mode)` | `deterministic_custom` | 39 | no | extra_dependency |
| `inspect_evals/threecb` | `best_elicitation_per_challenge()` | `deterministic_custom` | 35 | no | sandbox_required |
| `inspect_evals/truthfulqa` | `choice()` | `deterministic` | 817 | yes |  |
| `inspect_evals/uccb` | `model_graded_qa(template=UCCB_GRADING_TEMPLATE, model=scorer_model)` | `model_graded` | 1039 | no | model_graded |
| `inspect_evals/usaco` | `verify()` | `deterministic_custom` | 307 | no | sandbox_required |
| `inspect_evals/vimgolf_single_turn` | `vimgolf_scorer()` | `deterministic_custom` | 612 | no | sandbox_required |
| `inspect_evals/vqa_rad` | `vqa_rad_graded_scorer()` | `deterministic_custom` | 451 | yes |  |
| `inspect_evals/vstar_bench_attribute_recognition` | `choice()` | `deterministic` | 115 | yes |  |
| `inspect_evals/vstar_bench_spatial_relationship_reasoning` | `choice()` | `deterministic` | 76 | yes |  |
| `inspect_evals/winogrande` | `choice()` | `deterministic` | 1267 | yes |  |
| `inspect_evals/wmdp_bio` | `choice()` | `deterministic` | 1273 | yes |  |
| `inspect_evals/wmdp_chem` | `choice()` | `deterministic` | 408 | yes |  |
| `inspect_evals/wmdp_cyber` | `choice()` | `deterministic` | 1987 | yes |  |
| `inspect_evals/worldsense` | `pattern_with_metadata('^\\(?\\s*(1\|2\|3\|TRUE\|FALSE\|IMPOSSIBLE\|POSSIBLE)\\s*\\)?')` | `deterministic_custom` | 87048 | no | extra_dependency |
| `inspect_evals/writingbench` | `multi_scorer_wrapper(judge_model=judge_model)` | `model_graded` | 1000 | no | model_graded |
| `inspect_evals/xstest` | `model_graded_qa(model=scorer_model, template=scorer_template, instructions=scorer_instructions)` | `model_graded` | 250 | no | model_graded |
| `inspect_evals/zerobench` | `zerobench_scorer()` | `deterministic_custom` | 100 | no | gated_dataset |
| `inspect_evals/zerobench_subquestions` | `zerobench_scorer()` | `deterministic_custom` | 335 | no | gated_dataset |
