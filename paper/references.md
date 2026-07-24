# References

> Numbered in citation order. Inline citations in the paper use
> the form `[author, year]`; this file is the canonical
> bibliography.
>
> **Important:** the first draft of this bibliography contained
> three hallucinated citations (refs 7, 8, and 25 in the original
> numbering) — the ArcMemo author list and title, the Kiela 2019
> "compositionality challenge" reference, and the L2T/NEO paper
> title and first names. These were caught by the related-work
> reviewer (`reviews/03-related-work.md`) and have been replaced
> in this pass with the reviewer's supplied corrections. **The
> user should re-verify every replaced or newly-added citation
> against the source (arXiv / DOI / official page) before
> submission.** The corrections are flagged with `*(reviewer-
> supplied — verify)*` in the entries.

1. **Chollet, F.** (2019). *On the Measure of Intelligence.*
   arXiv:1911.01547. The framing of intelligence as
   skill-acquisition efficiency over a scope of tasks.

2. **Chollet, F.** (2019). The Abstraction and Reasoning Corpus
   (ARC). https://github.com/fchollet/ARC-AGI.

3. **Hodel, M.** (2024). *arc-dsl: a typed grid DSL for ARC.*
   https://github.com/michaelhodel/arc-dsl. The 160 typed grid
   primitives and the 400 hand-written reference solvers that
   are the clebran substrate's backbone.

4. **Ellis, K., Wong, C., Nye, M., Sable-Meyer, M., Cary, L.,
   Morales, L., Hewitt, L., Solar-Lezama, A., & Tenenbaum, J.B.**
   (2020). *DreamCoder: Growing generalizable, interpretable
   knowledge with wake-sleep Bayesian program learning.*
   arXiv:2006.08381.

5. **Bowers, M., Olaechea, T., constant, A., Drewniak, M., &
   Ellis, K.** (2023). *Stitch: A compositional framework for
   library learning.* arXiv:2211.16605.

6. **Lazaridou, A., & Baroni, M.** (2020). *Emergent Multi-Agent
   Communication in the Deep Learning Era.* arXiv:2006.02419.

7. **Brighton, H., & Kirby, S.** (2006). *Understanding
   Linguistic Evolution by Visualizing the Emergence of
   Topographic Mappings.* The original topographic-similarity
   paper; the metric the clebran project uses to measure
   compositionality of recovered vocabularies. *(reviewer-
   supplied — verify)*

8. **Lazaridou, A., Hermann, K.M., Tuyls, K., & Baroni, M.**
   (2018). *Emergence of Linguistic Communication from
   Referential Games with Symbolic and Pixel Input.* ICLR 2018.
   arXiv:1804.08784. Operationalises the topographic-similarity
   metric for emergent communication. *(reviewer-supplied —
   verify)*

9. **Chaabouni, R., Kharitonov, E., Bouchacourt, D., Dupoux, E.,
   & Baroni, M.** (2020). *Compositionality and Generalization
   In Emergent Languages.* ACL 2020. arXiv:2004.09124. The
   cleanest empirical demonstration that compositional
   structure (as measured by various proxies) is decoupled from
   generalisation. *(reviewer-supplied — verify)*

10. **Bouchacourt, D., & Baroni, M.** (2018). *How agents see
    things: On visual representations in an emergent language
    game.* EMNLP 2018. arXiv:1808.10696. The canonical
    demonstration that successful emergent communication does
    not entail compositionality — the original reference for
    the gap the clebran H3 null speaks to. *(reviewer-supplied —
    verify)*

11. **Li, F., & Bowling, M.** (2019). *Ease-of-Teaching and
    Language Structure from Emergent Communication.* NeurIPS
    2019. arXiv:1906.02403. The topsim–generalisation
    decoupling: topsim rises in the "reset" regime, but topsim
    does not perfectly predict task transfer. *(reviewer-supplied
    — verify)*

12. **Kirby, S., Tamariz, M., Smith, K., & Cornish, H.** (2015).
    *Compression and communication in the cultural evolution of
    linguistic structure.* Cognition 141, 87–102. The
    information-bottleneck theory of language — the canonical
    "constraint drives compositionality" claim the clebran H3
    null is in conversation with. *(reviewer-supplied — verify)*

13. **Baek, D., Lee, G., Baek, J., Lee, H., & Ahn, S.** (2026).
    *Learning to Theorize the World from Observation.* ICML 2026
    oral. arXiv:2605.03413. *(Title, first names, and venue
    corrected from the first-draft hallucination; reviewer-
    supplied — verify against the arXiv listing.)* L2T/NEO
    is the primary theoretical anchor for the clebran
    transfer-vs-reconstruction decomposition.

14. **Kharitonov, E., Chaabouni, R., Bouchacourt, D., & Baroni,
    M.** (2019). *EGG: a toolkit for research in Emergence of
    lanGuage in Games.* arXiv:1907.00852. The EGG framework
    paper; clebran adopts the topographic-similarity and
    discrete-channel framing from EGG. *(reviewer-supplied —
    verify)*

15. **Poli, R., Langdon, W.B., & McPhee, N.F.** (2008). *A Field
    Guide to Genetic Programming.* The standard reference for
    the population-based GP literature the clebran lineage model
    inherits.

16. **Potter, M.A., & De Jong, K.A.** (1994). *A cooperative
    coevolutionary approach to function optimization.* The
    parallel-evaluations framing for multi-population GP.

17. **Skolicki, Z., & De Jong, K.A.** (2005). *The influence of
    migration sizes and intervals on island models.* The
    migration-policy literature that the clebran adaptive
    operator selection answers.

18. **Jaderberg, M., Dalibard, V., Osindero, S., Czarnecki,
    W.M., Donahue, J., Razavi, A., Vinyals, O., Green, T.,
    Dunning, I., Simonyan, K., Fernando, C., & Kavukcuoglu, K.**
    (2017). *Population Based Training of Neural Networks.*
    arXiv:1711.09846. The modern neural-network-native analogue
    of island models. *(reviewer-supplied — verify)*

19. **Cully, A.** (2019). *Multi-Objective Quality-Diversity
    Optimisation.* In *Recent Developments in Evolutionary
    Optimisation in Modelling and Control.* The quality-
    diversity literature the clebran H1 (lineages diverge) is in
    conversation with. *(reviewer-supplied — verify)*

20. **Lehman, J., & Stanley, K.O.** (2011). *Abandoning
    Objectives: Evolution Through the Search for Novelty Alone.*
    Evolutionary Computation 19(2): 189–223. The novelty-search
    antecedent of the quality-diversity line. *(reviewer-supplied
    — verify)*

21. **McMahan, B., Moore, E., Ramage, D., Hampson, S., & y
    Arcas, B.A.** (2017). *Communication-Efficient Learning of
    Deep Networks from Decentralized Data.* AISTATS 2017.
    arXiv:1602.05629. The federated-learning analogue of
    multi-learner coordination. *(reviewer-supplied — verify)*

22. **Wang, R., Lehman, J., Clune, J., & Stanley, K.O.** (2019).
    *POET: Open-Ended Coevolution of Environments and their
    Optimized Solutions.* The asymmetric self-play framing for
    curriculum generation.

23. **Sukhbaatar, S., Denton, E., Szlam, A., & Fergus, R.**
    (2018). *Asymmetric self-play for automatic goal discovery
    in robotic manipulation.* The communication-through-tasks
    framing that the clebran curriculum channel extends.

24. **Dennis, M., Jaques, N., Vinitsky, E., Bayen, A., Russell,
    S., Critch, A., & Levine, S.** (2020). *Emergent Complexity
    and Zero-Shot Transfer via Unsupervised Environment Design.*
    NeurIPS 2020. PAIRED — the regret-based environment design
    literature.

25. **Parker-Holder, J., Jiang, N., Dennis, M., Samvelyan, M.,
    Foerster, J., Grefenstette, E., & Rocktäschel, T.** (2022).
    *Evolving Curricula with Regret-Based Environment Design.*
    arXiv:2203.01302. ACCEL — the closest existing analogue to
    the clebran adversarial/co-evolved curriculum generator.

26. **Portelas, R., Colas, C., Weng, L., Hofmann, K., & Oudeyer,
    P.-Y.** (2020). *Automatic Curriculum Learning for Deep RL:
    A Short Survey.* The automatic-curriculum-learning
    landscape.

27. **Narvekar, S., Peng, B., Leonetti, M., Sinapov, J., Taylor,
    M.E., & Stone, P.** (2020). *Curriculum Learning for RL:
    A Survey.* JMLR.

28. **Zhu, X.** (2015). *Machine Teaching: An Inverse Problem to
    Machine Learning and an Approach Toward Optimal Education.*
    The machine-teaching literature's founding reference.

29. **Liu, W., Dai, B., Humayun, A., Tay, C., Yu, C., Smith, L.,
    Rehg, J.M., & Song, L.** (2017). *Iterative Machine
    Teaching.* ICML 2017. arXiv:1705.10470.

30. **Garcia-Piqueras, M., & Hernández-Orallo, J.** (2021).
    *Optimal Teaching Curricula with Compositional Simplicity
    Priors.* ECML-PKDD 2021. The compositional-simplicity prior
    is the same MDL pressure that clebran's fitness function
    uses.

31. **Kirkpatrick, J., Pascanu, R., Rabinowitz, N., Veness, J.,
    Desjardins, G., Rusu, A.A., et al.** (2017). *Overcoming
    catastrophic forgetting in neural networks.* PNAS. The
    continual-learning / plasticity-loss literature the
    clebran 8b negative-transfer test operationalises.

32. **Schwarz, J., Czarnecki, W., Luketina, J., Grabska-
    Barwinska, A., Teh, Y.W., Pascanu, R., & Hadsell, R.**
    (2021). *Progress & Compress: A scalable framework for
    continual learning.* The continual-learning compress-then-
    expand framing.

33. **Wang, T., Zhu, J.-Y., Torralba, A., & Efros, A.A.** (2018).
    *Dataset Distillation.* The ML analogue of "export a tiny
    curriculum that teaches." arXiv:1811.10959.

34. **Sun, Y., Wang, X., Liu, Z., Miller, J., Efros, A., &
    Hardt, M.** (2020). *Test-Time Training with Self-
    Supervision.* ICLR 2020. The test-time-training antecedent
    of the TTT-for-ARC line. *(reviewer-supplied — verify)*

35. **Akyürek, E., Damani, M., Zweiger, A., Qiu, L., Guo, H.,
    Pari, J., Kim, Y., & Andreas, J.** (2024). *The Surprising
    Effectiveness of Test-Time Training for Few-Shot Learning.*
    arXiv:2411.07279. The 2024 ARC Prize second-place paper
    award; the direct neural-ARC competitor for the clebran
    "small-system acquisition cost" thesis. *(reviewer-supplied
    — verify)*

36. **Liao, I., & Gu, A.** (2025). *ARC-AGI Without Pretraining
    (CompressARC).* arXiv:2512.06104. 3rd place, ARC Prize
    2025; 76K parameters, no pretraining, no ARC training-set,
    solves 20% of the public evaluation set by minimising a
    variational description length. The direct competitor on
    the "intelligence as compression" axis. *(reviewer-supplied
    — verify)*

37. **Tenenbaum, J.B.** (1999). *A Bayesian Framework for
    Concept Learning.* PhD thesis, MIT. The Bayesian-program-
    learning antecedent DreamCoder and NEO inherit. *(reviewer-
    supplied — verify)*

38. **Goodman, N.D., Tenenbaum, J.B., Feldman, J., & Griffiths,
    T.L.** (2008). *A Rational Analysis of Generic Language
    Based on Bayesian Learning.* The Bayesian-LOT line.
    *(reviewer-supplied — verify)*

39. **Schmidhuber, J.** (1997). *Discovering Neural Nets with
    Low Kolmogorov Complexity and its Application to Time
    Series Prediction.* Neural Computation 10(3): 773–795. The
    compression-as-cognition / MDL antecedent. *(reviewer-
    supplied — verify)*

40. **Ho, M., Si, C., Feng, Z., Yu, F., Yang, Y., Liu, Z., Hu,
    Z., & Qin, L.** (2025). *ArcMemo: Abstract Reasoning
    Composition with Lifelong LLM Memory.* arXiv:2509.04439.
    The ArcMemo paper; clebran's central-library arm (B5) is
    the conceptual cousin. *(First-draft citation was a
    hallucination; replaced with reviewer-supplied correction
    — verify against the arXiv listing.)*

41. **Caruana, R.** (1997). *Multitask Learning.* Machine
    Learning 28(1): 41–75. The negative-transfer antecedent the
    clebran 8b / "irrelevant teaching hurts" result extends.
    *(reviewer-supplied — verify)*

42. **Standley, T., Zamir, A.R., Chen, D., Guibas, L., Malik,
    J., & Savarese, S.** (2020). *Which Tasks Should Be Learned
    Together in Multi-task Learning?* ICML 2020. The
    task-affinity negative-transfer result. *(reviewer-supplied
    — verify)*

43. **Lake, B.M., & Baroni, M.** (2018). *Generalization without
    Systematicity: On the Compositional Skills of Sequence-to-
    Sequence Recurrent Networks.* ICML 2018. The SCAN
    compositional-generalisation benchmark. *(reviewer-supplied
    — verify)*

44. **Kim, N., & Linzen, T.** (2020). *COGS: A Compositional
    Generalization Challenge Based on Semantic Interpretation.*
    EMNLP 2020. arXiv:2010.05465. The COGS benchmark.
    *(reviewer-supplied — verify)*

45. **Ruis, L., Andreas, J., Baroni, M., Bouchacourt, D., &
    Lake, B.M.** (2020). *A Benchmark for Systematic Generalization
    in Grounded Language Understanding.* NeurIPS 2020.
    arXiv:2003.09760. The gSCAN benchmark. *(reviewer-supplied
    — verify)*

46. **ARC Prize.** (2024–2026). https://arcprize.org/. The
    Kaggle competition context; the clebran design's compute
    target is the Kaggle envelope (~12h wall-clock, 4×L4 GPUs,
    offline only).
