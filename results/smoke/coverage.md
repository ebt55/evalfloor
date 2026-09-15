# Coverage

<!-- GENERATED FILE. Do not edit by hand. Regenerate with `evalfloor report`. Every number here is computed from results/sweep.json and rulings.jsonl. -->

The denominator comes before the result. Every task declared in an `eval.yaml` gets exactly one row here: it was swept, it is reachable but not yet swept, or there is a recorded reason it cannot be.

| provenance | value |
|---|---|
| `inspect_ai` | 0.3.263 |
| `inspect_evals` | 0.20.0 |
| battery fingerprint | `263b597d8f98` |
| sweep digest | `f38b0e4376f5ef27` |

## Totals

| | count |
|---|---|
| tasks declared in `eval.yaml` files | 237 |
| reachable for the deterministic sweep | 58 |
| excluded, with a reason | 179 |
| swept in this run | 5 |
| produced a scored floor | 5 |
| swept but errored | 0 |

## Exclusion reasons

| reason | tasks | meaning |
|---|---|---|
| `sandbox_required` | 76 | the task or its scorer needs a container |
| `extra_dependency` | 49 | needs an optional dependency group that is not installed |
| `model_graded` | 27 | the scorer needs a grader model; not part of the deterministic arm |
| `network_required` | 17 | fetches from a URL or clones a repository at run time |
| `gated_dataset` | 7 | the Hugging Face dataset requires accepting terms or an access grant |
| `too_large` | 3 | the dataset exceeds the disk cap recorded in PREREGISTRATION.md |

## Run failures

None. Every task attempted in this run produced a scored floor.

## Every task

| task | status | reason | detail |
|---|---|---|---|
| `inspect_evals/abstention_bench` | excluded | `extra_dependency` | eval.yaml: isolated: true (separate package) |
| `inspect_evals/agent_bench_os` | excluded | `network_required` | external assets: git_clone |
| `inspect_evals/agent_threat_bench_autonomy_hijack` | reachable, not swept | `` |  |
| `inspect_evals/agent_threat_bench_data_exfil` | reachable, not swept | `` |  |
| `inspect_evals/agent_threat_bench_memory_poison` | reachable, not swept | `` |  |
| `inspect_evals/agentdojo` | excluded | `extra_dependency` | eval.yaml: dependency: agentdojo |
| `inspect_evals/agentharm` | reachable, not swept | `` |  |
| `inspect_evals/agentharm_benign` | reachable, not swept | `` |  |
| `inspect_evals/agentic_misalignment` | excluded | `extra_dependency` | eval.yaml: dependency: agentic_misalignment |
| `inspect_evals/agie_aqua_rat` | excluded | `model_graded` | expression_equivalence: custom, calls a grader model; choice: inspect_ai builtin, pure function of completion and target |
| `inspect_evals/agie_logiqa_en` | excluded | `model_graded` | expression_equivalence: custom, calls a grader model; choice: inspect_ai builtin, pure function of completion and target |
| `inspect_evals/agie_lsat_ar` | excluded | `model_graded` | expression_equivalence: custom, calls a grader model; choice: inspect_ai builtin, pure function of completion and target |
| `inspect_evals/agie_lsat_lr` | excluded | `model_graded` | expression_equivalence: custom, calls a grader model; choice: inspect_ai builtin, pure function of completion and target |
| `inspect_evals/agie_lsat_rc` | excluded | `model_graded` | expression_equivalence: custom, calls a grader model; choice: inspect_ai builtin, pure function of completion and target |
| `inspect_evals/agie_math` | excluded | `model_graded` | expression_equivalence: custom, calls a grader model; choice: inspect_ai builtin, pure function of completion and target |
| `inspect_evals/agie_sat_en` | excluded | `model_graded` | expression_equivalence: custom, calls a grader model; choice: inspect_ai builtin, pure function of completion and target |
| `inspect_evals/agie_sat_en_without_passage` | excluded | `model_graded` | expression_equivalence: custom, calls a grader model; choice: inspect_ai builtin, pure function of completion and target |
| `inspect_evals/agie_sat_math` | excluded | `model_graded` | expression_equivalence: custom, calls a grader model; choice: inspect_ai builtin, pure function of completion and target |
| `inspect_evals/aime2024` | reachable, not swept | `` |  |
| `inspect_evals/aime2025` | reachable, not swept | `` |  |
| `inspect_evals/aime2026` | reachable, not swept | `` |  |
| `inspect_evals/air_bench` | reachable, not swept | `` |  |
| `inspect_evals/anima` | excluded | `extra_dependency` | eval.yaml: dependency: anima |
| `inspect_evals/ape_eval` | excluded | `network_required` | external assets: direct_url |
| `inspect_evals/apps` | excluded | `sandbox_required` | verify: custom, executes in a sandbox |
| `inspect_evals/arc_challenge` | reachable, not swept | `` |  |
| `inspect_evals/arc_easy` | reachable, not swept | `` |  |
| `inspect_evals/assistant_bench_closed_book_one_shot` | excluded | `sandbox_required` | eval directory ships a Dockerfile or compose file |
| `inspect_evals/assistant_bench_closed_book_zero_shot` | excluded | `sandbox_required` | eval directory ships a Dockerfile or compose file |
| `inspect_evals/assistant_bench_web_browser` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/assistant_bench_web_search_one_shot` | excluded | `sandbox_required` | eval directory ships a Dockerfile or compose file |
| `inspect_evals/assistant_bench_web_search_zero_shot` | excluded | `sandbox_required` | eval directory ships a Dockerfile or compose file |
| `inspect_evals/b3` | excluded | `extra_dependency` | eval.yaml: dependency: b3 |
| `inspect_evals/bbeh` | reachable, not swept | `` |  |
| `inspect_evals/bbeh_mini` | reachable, not swept | `` |  |
| `inspect_evals/bbh` | reachable, not swept | `` |  |
| `inspect_evals/bbq` | reachable, not swept | `` |  |
| `inspect_evals/bfcl` | excluded | `extra_dependency` | eval.yaml: dependency: bfcl |
| `inspect_evals/bfcl_prereqs` | excluded | `extra_dependency` | eval.yaml: dependency: bfcl |
| `inspect_evals/bigcodebench` | excluded | `sandbox_required` | verify: custom, executes in a sandbox |
| `inspect_evals/bold` | excluded | `extra_dependency` | eval.yaml: isolated: true (separate package) |
| `inspect_evals/boolq` | swept | `` |  |
| `inspect_evals/browse_comp` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/chembench` | reachable, not swept | `` |  |
| `inspect_evals/class_eval` | excluded | `sandbox_required` | class_eval_scorer: custom, executes in a sandbox |
| `inspect_evals/coconot` | excluded | `model_graded` | model_graded_qa: inspect_ai builtin grader |
| `inspect_evals/commonsense_qa` | reachable, not swept | `` |  |
| `inspect_evals/compute_eval` | excluded | `sandbox_required` | correctness_scorer: custom, executes in a sandbox |
| `inspect_evals/core_bench` | excluded | `sandbox_required` | evaluate_task_questions: custom, executes in a sandbox |
| `inspect_evals/cti_realm_25` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/cti_realm_25_minimal` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/cti_realm_25_seeded` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/cti_realm_50` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/cve_bench` | excluded | `extra_dependency` | eval.yaml: isolated: true (separate package) |
| `inspect_evals/cybench` | excluded | `extra_dependency` | eval.yaml: dependency: cybench |
| `inspect_evals/cybergym` | excluded | `sandbox_required` | cybergym_scorer: custom, executes in a sandbox |
| `inspect_evals/cybermetric_10000` | excluded | `network_required` | external assets: direct_url |
| `inspect_evals/cybermetric_2000` | excluded | `network_required` | external assets: direct_url |
| `inspect_evals/cybermetric_500` | excluded | `network_required` | external assets: direct_url |
| `inspect_evals/cybermetric_80` | excluded | `network_required` | external assets: direct_url |
| `inspect_evals/cyse2_interpreter_abuse` | excluded | `sandbox_required` | eval directory ships a Dockerfile or compose file |
| `inspect_evals/cyse2_prompt_injection` | excluded | `sandbox_required` | eval directory ships a Dockerfile or compose file |
| `inspect_evals/cyse2_vulnerability_exploit` | excluded | `sandbox_required` | vul_exploit_scorer: custom, executes in a sandbox |
| `inspect_evals/cyse3_visual_prompt_injection` | excluded | `model_graded` | model_graded_qa: inspect_ai builtin grader |
| `inspect_evals/cyse4_autocomplete` | excluded | `extra_dependency` | eval.yaml: dependency: cyberseceval_4 |
| `inspect_evals/cyse4_instruct` | excluded | `extra_dependency` | eval.yaml: dependency: cyberseceval_4 |
| `inspect_evals/cyse4_malware_analysis` | excluded | `extra_dependency` | eval.yaml: dependency: cyberseceval_4 |
| `inspect_evals/cyse4_mitre` | excluded | `extra_dependency` | eval.yaml: dependency: cyberseceval_4 |
| `inspect_evals/cyse4_mitre_frr` | excluded | `extra_dependency` | eval.yaml: dependency: cyberseceval_4 |
| `inspect_evals/cyse4_multilingual_prompt_injection` | excluded | `extra_dependency` | eval.yaml: dependency: cyberseceval_4 |
| `inspect_evals/cyse4_multiturn_phishing` | excluded | `extra_dependency` | eval.yaml: dependency: cyberseceval_4 |
| `inspect_evals/cyse4_threat_intelligence` | excluded | `extra_dependency` | eval.yaml: dependency: cyberseceval_4 |
| `inspect_evals/docvqa` | excluded | `too_large` | 11.27 GiB on the Hub, cap is 1.00 GiB |
| `inspect_evals/drop` | swept | `` |  |
| `inspect_evals/ds1000` | excluded | `sandbox_required` | ds1000_scorer: custom, executes in a sandbox |
| `inspect_evals/fortress_adversarial` | excluded | `model_graded` | fortress_scorer_adversarial: custom, calls a grader model |
| `inspect_evals/fortress_benign` | excluded | `model_graded` | fortress_scorer_benign: custom, calls a grader model |
| `inspect_evals/frontier_cs` | excluded | `sandbox_required` | frontier_cs_scorer: custom, executes in a sandbox |
| `inspect_evals/frontier_cs_algorithmic` | excluded | `sandbox_required` | frontier_cs_scorer: custom, executes in a sandbox |
| `inspect_evals/frontier_cs_research` | excluded | `sandbox_required` | frontier_cs_scorer: custom, executes in a sandbox |
| `inspect_evals/frontierscience` | excluded | `model_graded` | frontierscience_scorer: custom, calls a grader model |
| `inspect_evals/gaia` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/gaia_level1` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/gaia_level2` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/gaia_level3` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/gdm_classifier_evasion` | excluded | `sandbox_required` | scorer: custom, executes in a sandbox |
| `inspect_evals/gdm_cover_your_tracks` | excluded | `sandbox_required` | scorer: custom, executes in a sandbox |
| `inspect_evals/gdm_in_house_ctf` | excluded | `sandbox_required` | check_flag: custom, executes in a sandbox |
| `inspect_evals/gdm_intercode_ctf` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/gdm_oversight_pattern` | excluded | `sandbox_required` | scorer: custom, executes in a sandbox |
| `inspect_evals/gdm_self_reasoning_approved_directories` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/gdm_self_reasoning_calculator_improvement` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/gdm_self_reasoning_context_length_mod_instrumental_only` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/gdm_self_reasoning_context_length_mod_irreversibility_only` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/gdm_self_reasoning_database_tool` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/gdm_self_reasoning_latency_calculator` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/gdm_self_reasoning_max_messages_calculator` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/gdm_self_reasoning_max_tokens` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/gdm_self_reasoning_oversight_frequency` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/gdm_self_reasoning_read_logs` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/gdm_self_reasoning_turn_off_filters` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/gdm_sp01_e2e` | excluded | `extra_dependency` | eval.yaml: dependency: gdm_self_proliferation |
| `inspect_evals/gdm_sp02_e2e` | excluded | `extra_dependency` | eval.yaml: dependency: gdm_self_proliferation |
| `inspect_evals/gdm_sp03_e2e` | excluded | `extra_dependency` | eval.yaml: dependency: gdm_self_proliferation |
| `inspect_evals/gdm_sp04_e2e` | excluded | `extra_dependency` | eval.yaml: dependency: gdm_self_proliferation |
| `inspect_evals/gdm_sp05_e2e` | excluded | `extra_dependency` | eval.yaml: dependency: gdm_self_proliferation |
| `inspect_evals/gdm_sp07_e2e` | excluded | `extra_dependency` | eval.yaml: dependency: gdm_self_proliferation |
| `inspect_evals/gdm_sp08_e2e` | excluded | `extra_dependency` | eval.yaml: dependency: gdm_self_proliferation |
| `inspect_evals/gdm_sp09_e2e` | excluded | `extra_dependency` | eval.yaml: dependency: gdm_self_proliferation |
| `inspect_evals/gdm_sp10_e2e` | excluded | `extra_dependency` | eval.yaml: dependency: gdm_self_proliferation |
| `inspect_evals/gdm_sp12_e2e` | excluded | `extra_dependency` | eval.yaml: dependency: gdm_self_proliferation |
| `inspect_evals/gdm_strategic_rule_breaking` | excluded | `sandbox_required` | scorer: custom, executes in a sandbox |
| `inspect_evals/gdpval` | excluded | `sandbox_required` | scorer: custom, executes in a sandbox |
| `inspect_evals/gpqa_diamond` | excluded | `network_required` | external assets: direct_url |
| `inspect_evals/gsm8k` | swept | `` |  |
| `inspect_evals/healthbench` | excluded | `extra_dependency` | eval.yaml: dependency: healthbench |
| `inspect_evals/healthbench_consensus` | excluded | `extra_dependency` | eval.yaml: dependency: healthbench |
| `inspect_evals/healthbench_hard` | excluded | `extra_dependency` | eval.yaml: dependency: healthbench |
| `inspect_evals/healthbench_meta_eval` | excluded | `extra_dependency` | eval.yaml: dependency: healthbench |
| `inspect_evals/hellaswag` | reachable, not swept | `` |  |
| `inspect_evals/hle` | excluded | `gated_dataset` | gated on the Hub: cais/hle, skylenage-ai/HLE-Verified, cais/hle-rolling |
| `inspect_evals/humaneval` | excluded | `sandbox_required` | verify: custom, executes in a sandbox |
| `inspect_evals/ifeval` | excluded | `extra_dependency` | eval.yaml: dependency: ifeval |
| `inspect_evals/ifevalcode` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/infinite_bench_code_debug` | excluded | `sandbox_required` | scorer: custom, executes in a sandbox |
| `inspect_evals/infinite_bench_code_run` | excluded | `sandbox_required` | scorer: custom, executes in a sandbox |
| `inspect_evals/infinite_bench_kv_retrieval` | excluded | `sandbox_required` | scorer: custom, executes in a sandbox |
| `inspect_evals/infinite_bench_longbook_choice_eng` | excluded | `sandbox_required` | scorer: custom, executes in a sandbox |
| `inspect_evals/infinite_bench_longdialogue_qa_eng` | excluded | `sandbox_required` | scorer: custom, executes in a sandbox |
| `inspect_evals/infinite_bench_math_calc` | excluded | `sandbox_required` | scorer: custom, executes in a sandbox |
| `inspect_evals/infinite_bench_math_find` | excluded | `sandbox_required` | scorer: custom, executes in a sandbox |
| `inspect_evals/infinite_bench_number_string` | excluded | `sandbox_required` | scorer: custom, executes in a sandbox |
| `inspect_evals/infinite_bench_passkey` | excluded | `sandbox_required` | scorer: custom, executes in a sandbox |
| `inspect_evals/instrumentaleval` | excluded | `model_graded` | instrumentaleval_scorer: custom, calls a grader model; get_model: custom, definition not found in this eval package; GenerateConfig: custom, |
| `inspect_evals/ipi_coding_agent` | excluded | `sandbox_required` | ipi_scorer: custom, executes in a sandbox |
| `inspect_evals/kernelbench` | excluded | `sandbox_required` | kernelbench_scorer: custom, executes in a sandbox |
| `inspect_evals/lab_bench_cloning_scenarios` | reachable, not swept | `` |  |
| `inspect_evals/lab_bench_dbqa` | reachable, not swept | `` |  |
| `inspect_evals/lab_bench_figqa` | reachable, not swept | `` |  |
| `inspect_evals/lab_bench_litqa` | reachable, not swept | `` |  |
| `inspect_evals/lab_bench_protocolqa` | reachable, not swept | `` |  |
| `inspect_evals/lab_bench_seqqa` | reachable, not swept | `` |  |
| `inspect_evals/lab_bench_suppqa` | reachable, not swept | `` |  |
| `inspect_evals/lab_bench_tableqa` | reachable, not swept | `` |  |
| `inspect_evals/lingoly` | excluded | `gated_dataset` | gated on the Hub: ambean/lingOly, jkhouja/LingOly-TOO |
| `inspect_evals/lingoly_too` | excluded | `gated_dataset` | gated on the Hub: ambean/lingOly, jkhouja/LingOly-TOO |
| `inspect_evals/livebench` | excluded | `extra_dependency` | eval.yaml: isolated: true (separate package) |
| `inspect_evals/livecodebench_pro` | excluded | `sandbox_required` | livecodebench_pro_scorer: custom, executes in a sandbox |
| `inspect_evals/macbench` | reachable, not swept | `` |  |
| `inspect_evals/make_me_pay` | reachable, not swept | `` |  |
| `inspect_evals/makemesay` | excluded | `extra_dependency` | eval.yaml: dependency: makemesay |
| `inspect_evals/mask` | excluded | `model_graded` | accuracy_and_honesty: custom, calls a grader model; NoBeliefConsistencyHandling: custom, definition not found in this eval package |
| `inspect_evals/math` | excluded | `extra_dependency` | eval.yaml: dependency: math |
| `inspect_evals/mathvista` | excluded | `too_large` | 1.63 GiB on the Hub, cap is 1.00 GiB |
| `inspect_evals/mbpp` | excluded | `sandbox_required` | verify: custom, executes in a sandbox |
| `inspect_evals/medqa` | excluded | `extra_dependency` | eval.yaml: dependency: medqa |
| `inspect_evals/mgsm` | excluded | `network_required` | external assets: direct_url |
| `inspect_evals/mind2web` | excluded | `extra_dependency` | eval.yaml: dependency: mind2web |
| `inspect_evals/mind2web_sc` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/mle_bench` | excluded | `sandbox_required` | mle_bench_scorer: custom, executes in a sandbox |
| `inspect_evals/mle_bench_full` | excluded | `sandbox_required` | mle_bench_scorer: custom, executes in a sandbox |
| `inspect_evals/mle_bench_lite` | excluded | `sandbox_required` | mle_bench_scorer: custom, executes in a sandbox |
| `inspect_evals/mlrc_bench` | excluded | `sandbox_required` | mlrc_scorer: custom, executes in a sandbox |
| `inspect_evals/mmiu` | excluded | `network_required` | external assets: direct_url |
| `inspect_evals/mmlu_0_shot` | reachable, not swept | `` |  |
| `inspect_evals/mmlu_5_shot` | reachable, not swept | `` |  |
| `inspect_evals/mmlu_pro` | reachable, not swept | `` |  |
| `inspect_evals/mmmu_multiple_choice` | excluded | `too_large` | 3.40 GiB on the Hub, cap is 1.00 GiB |
| `inspect_evals/mmmu_open` | excluded | `model_graded` | model_graded_fact: inspect_ai builtin grader |
| `inspect_evals/moru` | excluded | `model_graded` | moru_scorer: custom, calls a grader model |
| `inspect_evals/musr` | reachable, not swept | `` |  |
| `inspect_evals/niah` | excluded | `extra_dependency` | eval.yaml: dependency: niah |
| `inspect_evals/novelty_bench` | excluded | `extra_dependency` | eval.yaml: isolated: true (separate package) |
| `inspect_evals/onet_m6` | reachable, not swept | `` |  |
| `inspect_evals/osworld` | excluded | `sandbox_required` | osworld_scorer: custom, executes in a sandbox |
| `inspect_evals/osworld_small` | excluded | `sandbox_required` | osworld_scorer: custom, executes in a sandbox |
| `inspect_evals/paperbench` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/paws` | swept | `` |  |
| `inspect_evals/persistbench_beneficial_memory` | excluded | `model_graded` | persistbench_judge: custom, calls a grader model |
| `inspect_evals/persistbench_cross_domain` | excluded | `model_graded` | persistbench_judge: custom, calls a grader model |
| `inspect_evals/persistbench_sycophancy` | excluded | `model_graded` | persistbench_judge: custom, calls a grader model |
| `inspect_evals/personality_BFI` | excluded | `extra_dependency` | eval.yaml: dependency: personality |
| `inspect_evals/personality_TRAIT` | excluded | `extra_dependency` | eval.yaml: dependency: personality |
| `inspect_evals/piqa` | excluded | `network_required` | external assets: direct_url |
| `inspect_evals/pre_flight` | reachable, not swept | `` |  |
| `inspect_evals/pubmedqa` | reachable, not swept | `` |  |
| `inspect_evals/race_h` | reachable, not swept | `` |  |
| `inspect_evals/sad_facts_human_defaults` | excluded | `network_required` | external assets: direct_url |
| `inspect_evals/sad_facts_llms` | excluded | `network_required` | external assets: direct_url |
| `inspect_evals/sad_influence` | excluded | `network_required` | external assets: direct_url |
| `inspect_evals/sad_stages_full` | excluded | `network_required` | external assets: direct_url |
| `inspect_evals/sad_stages_oversight` | excluded | `network_required` | external assets: direct_url |
| `inspect_evals/scbench` | excluded | `sandbox_required` | scbench_scorer: custom, executes in a sandbox |
| `inspect_evals/scicode` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/sciknoweval` | excluded | `extra_dependency` | eval.yaml: dependency: sciknoweval |
| `inspect_evals/sec_qa_v1` | reachable, not swept | `` |  |
| `inspect_evals/sec_qa_v1_5_shot` | reachable, not swept | `` |  |
| `inspect_evals/sec_qa_v2` | swept | `` |  |
| `inspect_evals/sec_qa_v2_5_shot` | reachable, not swept | `` |  |
| `inspect_evals/sevenllm_mcq_en` | excluded | `extra_dependency` | eval.yaml: dependency: sevenllm |
| `inspect_evals/sevenllm_mcq_zh` | excluded | `extra_dependency` | eval.yaml: dependency: sevenllm |
| `inspect_evals/sevenllm_qa_en` | excluded | `extra_dependency` | eval.yaml: dependency: sevenllm |
| `inspect_evals/sevenllm_qa_zh` | excluded | `extra_dependency` | eval.yaml: dependency: sevenllm |
| `inspect_evals/simpleqa` | excluded | `network_required` | external assets: direct_url |
| `inspect_evals/simpleqa_verified` | excluded | `network_required` | external assets: direct_url |
| `inspect_evals/sosbench` | excluded | `model_graded` | llm_judge_scorer: custom, calls a grader model |
| `inspect_evals/squad` | reachable, not swept | `` |  |
| `inspect_evals/stereoset` | reachable, not swept | `` |  |
| `inspect_evals/strong_reject` | excluded | `model_graded` | strong_reject_scorer: custom, calls a grader model |
| `inspect_evals/swe_bench` | excluded | `sandbox_required` | swe_bench_scorer: custom, executes in a sandbox |
| `inspect_evals/swe_bench_verified_mini` | excluded | `sandbox_required` | swe_bench_scorer: custom, executes in a sandbox |
| `inspect_evals/swe_lancer` | excluded | `sandbox_required` | debug_artifact_exporter: custom, executes in a sandbox |
| `inspect_evals/sycophancy` | excluded | `model_graded` | sycophancy_scorer: custom, calls a grader model |
| `inspect_evals/tac` | excluded | `gated_dataset` | gated on the Hub: CompassioninMachineLearning/tac |
| `inspect_evals/tac_welfare` | excluded | `gated_dataset` | gated on the Hub: CompassioninMachineLearning/tac |
| `inspect_evals/tau2_airline` | reachable, not swept | `` |  |
| `inspect_evals/tau2_banking` | reachable, not swept | `` |  |
| `inspect_evals/tau2_retail` | reachable, not swept | `` |  |
| `inspect_evals/tau2_telecom` | reachable, not swept | `` |  |
| `inspect_evals/theagentcompany` | excluded | `extra_dependency` | eval.yaml: dependency: theagentcompany |
| `inspect_evals/threecb` | excluded | `sandbox_required` | eval directory ships a Dockerfile or compose file |
| `inspect_evals/truthfulqa` | reachable, not swept | `` |  |
| `inspect_evals/uccb` | excluded | `model_graded` | model_graded_qa: inspect_ai builtin grader |
| `inspect_evals/usaco` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/vimgolf_single_turn` | excluded | `sandbox_required` | task declares sandbox= |
| `inspect_evals/vqa_rad` | reachable, not swept | `` |  |
| `inspect_evals/vstar_bench_attribute_recognition` | reachable, not swept | `` |  |
| `inspect_evals/vstar_bench_spatial_relationship_reasoning` | reachable, not swept | `` |  |
| `inspect_evals/winogrande` | reachable, not swept | `` |  |
| `inspect_evals/wmdp_bio` | reachable, not swept | `` |  |
| `inspect_evals/wmdp_chem` | reachable, not swept | `` |  |
| `inspect_evals/wmdp_cyber` | reachable, not swept | `` |  |
| `inspect_evals/worldsense` | excluded | `extra_dependency` | eval.yaml: dependency: worldsense |
| `inspect_evals/writingbench` | excluded | `model_graded` | multi_scorer_wrapper: custom, calls a grader model |
| `inspect_evals/xstest` | excluded | `model_graded` | model_graded_qa: inspect_ai builtin grader |
| `inspect_evals/zerobench` | excluded | `gated_dataset` | gated on the Hub: jonathan-roberts1/zerobench |
| `inspect_evals/zerobench_subquestions` | excluded | `gated_dataset` | gated on the Hub: jonathan-roberts1/zerobench |
