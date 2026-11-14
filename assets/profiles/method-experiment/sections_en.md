# Method-and-Experiment Paper Section Templates

## 1. Abstract

State the task, testable gap, core method, data and comparisons, key quantitative results, and scope. Include at least one primary metric with a baseline. Use `{pending}` when experiments are incomplete; do not present expectations as results.

## 2. Introduction

Move from problem impact to limitations of existing methods, a testable gap, the proposed idea, and evidence-linked contributions. Limit contributions to method components, experimental/evaluation design, and validated findings.

## 3. Related Work

Organize by method families: conventional or physical approaches, data-driven methods, prior/physics integration, and generalization or uncertainty. Compare inputs, outputs, training demand, evaluation settings, and failure conditions. End with one precise gap advanced by this study.

## 4. Methodology

Recommended subsections: problem formulation and notation; data generation/preprocessing/splits; overall architecture; key components and motivation; objectives and constraints; training and inference; parameters, complexity, hardware, and reproducibility. Explain the failure mode addressed before each component.

## 5. Experimental Design

Specify leakage-free splits, strong baselines, fair training settings, task-aligned metrics, ablations, robustness/generalization tests, and repeated-run or statistical procedures. Main, ablation, and sensitivity experiments should answer whether, why, and when the method works.

## 6. Results and Analysis

Order evidence as main comparison, ablation, robustness/generalization, error analysis, efficiency, and interpretability or uncertainty. Report absolute and relative changes, variation or intervals, and repetitions. Training performance is not generalization evidence.

## 7. Discussion

Discuss mechanisms and alternative explanations, differences from representative methods, deployment conditions, negative results, and failure scenarios. Distinguish fidelity to a reference dataset or simulator from real-world truth.

## 8. Conclusion

Answer each research question and retain only contributions supported by main, ablation, or robustness evidence. State boundaries in data, scenario, scale, and reference frame; avoid universal claims.
