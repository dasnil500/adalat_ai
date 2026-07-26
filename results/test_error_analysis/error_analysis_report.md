# Full-Test Inference Error Analysis

Generated: 2026-07-26T14:02:17

## Run Metadata

| Field | Value |
| --- | --- |
| Corpus | Indian court judgment parallel corpus |
| Language pair | English-to-Hindi |
| Test segments | 45 |
| Metric implementation | sacrebleu |
| Model | /home/gpuuser0/gpuuser0_a/NMD/adalat_ai/checkpoints/final_model |

## Corpus-Level Metrics

| Metric | Value |
| --- | --- |
| BLEU | 23.86 |
| chrF | 51.27 |
| Mean length ratio | 0.9837 |
| Median length ratio | 0.9744 |
| Mean token-overlap F1 | 0.5854 |
| Mean legal-group preservation | 0.8994 |

## Error Taxonomy Summary

| Category | Family | Severity | Multi-label n | % | Primary n |
| --- | --- | --- | --- | --- | --- |
| repetition_or_fluency_error | fluency_script | medium | 33 | 73.33% | 2 |
| legal_terminology_omission | legal_domain_fidelity | high | 24 | 53.33% | 22 |
| legal_terminology_addition | legal_domain_fidelity | medium | 23 | 51.11% | 7 |
| named_entity_or_abbreviation_risk | factual_preservation | medium | 17 | 37.78% | 2 |
| outcome_error | legal_domain_fidelity | high | 10 | 22.22% | 0 |
| date_number_error | factual_preservation | medium | 9 | 20.0% | 1 |
| negation_modality_error | legal_reasoning | high | 8 | 17.78% | 0 |
| acceptable_or_minor_variation | minor | low | 8 | 17.78% | 8 |
| wrong_script_or_source_copying | fluency_script | critical | 3 | 6.67% | 3 |
| party_role_error | legal_domain_fidelity | high | 3 | 6.67% | 0 |
| statutory_reference_error | legal_domain_fidelity | high | 3 | 6.67% | 0 |
| under_translation_omission | adequacy | high | 2 | 4.44% | 0 |
| over_translation_addition | adequacy | high | 1 | 2.22% | 0 |
| format_structure_error | structure | medium | 1 | 2.22% | 0 |

## Paper-Ready Interpretation

We evaluated the system on the full held-out test split of an Indian court judgment English-Hindi parallel corpus, comprising 45 aligned legal text segments. At corpus level, the system obtained BLEU=23.86 and chrF=51.27, with a mean hypothesis/reference length ratio of 0.9837. These metrics were complemented with a multi-label legal error taxonomy, because general-purpose MT scores do not directly capture legally consequential failures such as party-role shifts, statutory-reference loss, or incorrect judicial outcomes.

The most frequent error category was `repetition_or_fluency_error` (33/45, 73.33%). Across the taxonomy, the dominant error families were legal_domain_fidelity (63), fluency_script (36), factual_preservation (26), minor (8), legal_reasoning (8). This indicates that the analysis should not be framed only as a fluency problem; a substantial part of the error profile concerns adequacy and domain fidelity.

For legal-domain fidelity, the script explicitly tracks whether concepts such as appeal, petition/writ, party roles, court/forum names, statutory references, charges, evidence, and judicial outcomes are preserved. Missing legal groups are especially important for Indian court judgments because mistranslating an appellant as a respondent, dropping a section/article reference, or changing whether a matter was dismissed or allowed can alter the legal proposition conveyed by the translation.

For factual preservation, the analysis separately flags dates, numbers, statutory-reference numbers, abbreviations, and named-entity risk. These errors are treated separately from generic semantic drift because court judgments are citation-heavy documents: years, sections, charge-sheet dates, FIR references, and case identifiers often carry central evidentiary or procedural meaning.

The taxonomy is heuristic and should be used as a structured first pass before manual adjudication. It is nevertheless useful for a research paper because it produces reproducible counts, keeps each segment's evidence, and separates legally material errors from ordinary lexical variation.

## Most Frequently Missing Legal Groups

| Legal group | Missing count |
| --- | --- |
| modality_direction | 5 |
| judge_bench | 4 |
| dismissal_rejection | 3 |
| reasoning_connective | 3 |
| conviction_sentence | 3 |
| set_aside_quash | 3 |
| charge_fir | 3 |
| accused_party | 2 |
| statutory_reference | 2 |
| evidence_witness | 2 |
| allowed_relief | 2 |
| petition_writ | 2 |

## Category Definitions

| Category | Family | Severity | Definition |
| --- | --- | --- | --- |
| empty_or_degenerate_output | fluency_script | critical | The system produced an empty, near-empty, or otherwise unusable output. |
| wrong_script_or_source_copying | fluency_script | critical | The output remains substantially in English/Latin script or copies the source. |
| severe_semantic_drift | adequacy | critical | The output has very low character and token overlap with the reference. |
| under_translation_omission | adequacy | high | The output is materially shorter than the reference, suggesting omitted legal content. |
| over_translation_addition | adequacy | high | The output is materially longer than the reference or adds unsupported content. |
| legal_terminology_omission | legal_domain_fidelity | high | Expected legal concepts are missing from the hypothesis. |
| legal_terminology_addition | legal_domain_fidelity | medium | The hypothesis introduces legal concepts not observed in the source/reference. |
| party_role_error | legal_domain_fidelity | high | Party roles such as appellant, respondent, petitioner, or accused are dropped or altered. |
| statutory_reference_error | legal_domain_fidelity | high | Sections, articles, Acts, rules, or code references are not preserved. |
| outcome_error | legal_domain_fidelity | high | Disposition/outcome terms such as allowed, dismissed, quashed, conviction, or bail are mistranslated. |
| negation_modality_error | legal_reasoning | high | Negation, obligation, permission, entitlement, or judicial direction is missing or added. |
| date_number_error | factual_preservation | medium | Dates, amounts, paragraph numbers, years, or other numeric facts are not preserved. |
| named_entity_or_abbreviation_risk | factual_preservation | medium | Names, institutions, or legal abbreviations in the source are at risk of being lost or distorted. |
| repetition_or_fluency_error | fluency_script | medium | The output contains repeated words/phrases or visibly degraded fluency. |
| format_structure_error | structure | medium | Paragraph numbering, list markers, or enumerated legal structure are not preserved. |
| acceptable_or_minor_variation | minor | low | No major heuristic error was detected; remaining issues are likely lexical/style variation. |

## Representative Error Examples

### legal_terminology_omission

Family: legal_domain_fidelity | Severity: high

- Index 43 | doc=21 | segment=7 | BLEU=8.17 | chrF=35.97
  Evidence: Missing expected legal groups: charge_fir
  EN: 11. In frivolous or vexatious proceedings, the court owes a duty to look into many other attending circumstances emerging from the record of the case over and above the averments and, if need be, with due care and circumspection try to r...
  REF: 11. बुच्छ या परेशान करने वाली कार्यवाहियों में. न्यायालय का यह कर्तव्य है कि वह मायले के अभिलेख से कथनों के आतिरिक्त अन्य अनेक परिस्थितियों पर भी योर करे ऑर यदि आवश्यक हो तो. पूरी सावधानी ऑर सतर्कता के साथ पंक्तियों के बीच के अर्थ को समझ...
  HYP: 11. अनाधिकृत या षड्यंत्रित कार्यवाही में, न्यायालय को पीड़ितों के साथ उत्पन्न कई अन्य घटनाओं पर गौर करने की जिम्मेदारी है और यदि आवश्यकता है, तो उचित संज्ञान और परिस्थितियों के साथ-साथ लाइन के बीच पढ़ा जाना चाहिए। न्यायालय जब सीआरपीसी की...
- Index 24 | doc=4 | segment=6 | BLEU=12.63 | chrF=39.27
  Evidence: Missing expected legal groups: judge_bench
  EN: 7 The writ petition filed by the appellant was dismissed by a learned Single Judge of the High Court on 9 October 2013. The appellant filed a Special Appeal against the dismissal of the petition.
  REF: 7. अभ्यर्थी द्वारा दायर रिट याचिका दिनांक 9 अक्टूबर 2013 को माननीय उच्च न्यायालय के विद्गत एकल न्यायाधीश द्वारा निरस्त कर दिया गया। याचिका के निरस्तीकरण के विरुद्ध अपीलार्थी ने विशेष याचिका दायर की।
  HYP: 7. अपीलकर्ता द्वारा दायर रिट याचिका को उच्च न्यायालय द्वारा 9 October 2013 को खारिज कर दिया गया था। अपीलकर्ता ने याचिका को खारिज करने के खिलाफ विशेष अपील दायर की।
- Index 35 | doc=4 | segment=17 | BLEU=18.89 | chrF=42.54
  Evidence: Missing expected legal groups: reasoning_connective
  EN: 18 The appeal is accordingly disposed of in the above terms. Pending application(s), if any, shall stand disposed of. There shall be no order as to costs.
  REF: 18. यह अपील तदनुरूप उपरोक्त शर्तों के आधार पर निस्तारित की जाती है। यदि कोई आवेदन लंबित रहता है तो भी वह निस्तारित माना जाएगा, खर्चे के लिए कोई आदेश नहीं होगा।
  HYP: 18. अपील उपरोक्त निबंधनों में निस्तारित है। लंबित आवेदन (ओं), यदि कोई हों, का निस्तारण किया जाना है। लागत के लिए कोई आदेश नहीं होगा।

### negation_modality_error

Family: legal_reasoning | Severity: high

- Index 43 | doc=21 | segment=7 | BLEU=8.17 | chrF=35.97
  Evidence: Negation/modality mismatch: modality_direction
  EN: 11. In frivolous or vexatious proceedings, the court owes a duty to look into many other attending circumstances emerging from the record of the case over and above the averments and, if need be, with due care and circumspection try to r...
  REF: 11. बुच्छ या परेशान करने वाली कार्यवाहियों में. न्यायालय का यह कर्तव्य है कि वह मायले के अभिलेख से कथनों के आतिरिक्त अन्य अनेक परिस्थितियों पर भी योर करे ऑर यदि आवश्यक हो तो. पूरी सावधानी ऑर सतर्कता के साथ पंक्तियों के बीच के अर्थ को समझ...
  HYP: 11. अनाधिकृत या षड्यंत्रित कार्यवाही में, न्यायालय को पीड़ितों के साथ उत्पन्न कई अन्य घटनाओं पर गौर करने की जिम्मेदारी है और यदि आवश्यकता है, तो उचित संज्ञान और परिस्थितियों के साथ-साथ लाइन के बीच पढ़ा जाना चाहिए। न्यायालय जब सीआरपीसी की...
- Index 30 | doc=4 | segment=12 | BLEU=6.05 | chrF=42.72
  Evidence: Negation/modality mismatch: modality_direction
  EN: 13 On the other hand, it has been urged Mr. Tanmaya Agarwal, learned Senior Counsel appearing on behalf of the first respondent that the High Court has correctly come to the conclusion that the ad hoc appointment of the appellant could n...
  REF: 13. दूसरी ओर प्रथम प्रत्यर्थी के वरिष्ठ विद्वान अधिवक्ता श्री न्मय अग्रवाल ने तर्क दिया है कि माननीय उच्च न्यायालय का निष्कर्ष सही है कि अपीलार्थी की तदर्थ नियुक्ति किसी भी परिस्थिति में उस समय के पद धारक की मृत्यु पर मौलिक नियुक्ति नहीं...
  HYP: 13 दूसरी ओर, यह अनुरोध किया गया है कि प्रथम प्रत्यर्थी की ओर से पेश हुए विद्वान वरिष्ठ अधिवक्ता श्री तनन् ्मय अग्रवाल से यह सही ढंग से निर्णय लिया गया है कि अपीलकर्ता की अधिमानतः की गई प्रार्थना पत्र में, किसी भी मामले में, तत्कालीन प्रत...
- Index 25 | doc=4 | segment=7 | BLEU=10.43 | chrF=43.59
  Evidence: Negation/modality mismatch: modality_direction
  EN: 8 During the pendency of the Special Appeal, there was an interim order in favour of the appellant in terms similar to the interim protection which was granted earlier on 16 April 1996 by the Single Judge of the High Court. By the impugn...
  REF: 8. विशेष याचिका के लंबन के दौरान अंतरिम इस अंतरिम सुरक्षा के शर्तों की तरह अपीलार्थी के पक्ष में एक अंतरिम आदेश जो कि 16 अप्रैल 1996 के पूर्व माननीय उच्च न्यायालय के एकल न्यायाधीश द्वारा प्रदान की गई। आक्षेपित आदेश दिनांक 30 अक्टूबर 2017...
  HYP: 8. विशेष अपील के लम्बन के दौरान, अपीलकर्ता के पक्ष में आंशिक एवं दीर्घकालिक प्रावधान, जो उच्च न्यायालय के एकमात्र न्यायाधीश द्वारा 16 अप्रैल 1996 को दिया गया था, के संदर्भ में आंशिक प्रावधान था। आक्षेपित आदेश दिनांक 30 October 2017 द्वार...

### under_translation_omission

Family: adequacy | Severity: high

- Index 43 | doc=21 | segment=7 | BLEU=8.17 | chrF=35.97
  Evidence: Length ratio=0.6025; hypothesis is much shorter than reference.
  EN: 11. In frivolous or vexatious proceedings, the court owes a duty to look into many other attending circumstances emerging from the record of the case over and above the averments and, if need be, with due care and circumspection try to r...
  REF: 11. बुच्छ या परेशान करने वाली कार्यवाहियों में. न्यायालय का यह कर्तव्य है कि वह मायले के अभिलेख से कथनों के आतिरिक्त अन्य अनेक परिस्थितियों पर भी योर करे ऑर यदि आवश्यक हो तो. पूरी सावधानी ऑर सतर्कता के साथ पंक्तियों के बीच के अर्थ को समझ...
  HYP: 11. अनाधिकृत या षड्यंत्रित कार्यवाही में, न्यायालय को पीड़ितों के साथ उत्पन्न कई अन्य घटनाओं पर गौर करने की जिम्मेदारी है और यदि आवश्यकता है, तो उचित संज्ञान और परिस्थितियों के साथ-साथ लाइन के बीच पढ़ा जाना चाहिए। न्यायालय जब सीआरपीसी की...
- Index 8 | doc=1 | segment=7 | BLEU=19.58 | chrF=47.25
  Evidence: Length ratio=0.625; hypothesis is much shorter than reference.
  EN: 5. The penalty of reduction of pay of 15 stages was challenged by the Appellant by filing a Writ Petition. The High Court allowed the Writ Petition and directed the Respondent-Disciplinary Authority to re-examine the matter afresh. The D...
  REF: 5. रिट याचिका दायर करके अपीलकर्ता द्वारा 15 चरणों के वेतन में कमी के दंड को चुनौती दी गई थी। उच्च न्यायालय ने रिट याचिका की अनुमति दी और प्रत्यर्थी - अनुशासनात्मक प्राधिकरण को मामले को नए सिरे से जांचने का निर्देश दिया। अनुशासन प्राधिकरण...
  HYP: 5. 15 स्तरों के pay को चुनौती देने के लिए अपीलकर्ता द्वारा एक रिट याचिका दायर करके माफ़ी का मुकदमा चुनौती दी गई। उच्च न्यायालय ने रिट याचिका को स्वीकार किया और प्रतिवादी-निगमात्मक प्राधिकारी को मामले को नए सिरे से विनिश्चित करने के लिए न...

### legal_terminology_addition

Family: legal_domain_fidelity | Severity: medium

- Index 43 | doc=21 | segment=7 | BLEU=8.17 | chrF=35.97
  Evidence: Added legal groups not seen in source/reference: modality_direction
  EN: 11. In frivolous or vexatious proceedings, the court owes a duty to look into many other attending circumstances emerging from the record of the case over and above the averments and, if need be, with due care and circumspection try to r...
  REF: 11. बुच्छ या परेशान करने वाली कार्यवाहियों में. न्यायालय का यह कर्तव्य है कि वह मायले के अभिलेख से कथनों के आतिरिक्त अन्य अनेक परिस्थितियों पर भी योर करे ऑर यदि आवश्यक हो तो. पूरी सावधानी ऑर सतर्कता के साथ पंक्तियों के बीच के अर्थ को समझ...
  HYP: 11. अनाधिकृत या षड्यंत्रित कार्यवाही में, न्यायालय को पीड़ितों के साथ उत्पन्न कई अन्य घटनाओं पर गौर करने की जिम्मेदारी है और यदि आवश्यकता है, तो उचित संज्ञान और परिस्थितियों के साथ-साथ लाइन के बीच पढ़ा जाना चाहिए। न्यायालय जब सीआरपीसी की...
- Index 31 | doc=4 | segment=13 | BLEU=3.41 | chrF=38.31
  Evidence: Added legal groups not seen in source/reference: dismissal_rejection, set_aside_quash, statutory_reference
  EN: 14 The appellant was appointed purely on an ad hoc basis in a leave vacancy which arose in the institution. On the death of the regularly appointed candidate, the leave vacancy ceased to exist. Once a substantive vacancy arose, it was re...
  REF: 14. अपीलार्थी को इस संस्थान में रिक्त पद पर पूर्णतः अस्थाई तौर पर नियुक्त किया गया। अस्थाई रूप से अभ्यर्थी की नियुक्ति होते ही रिक्त पद समाप्त हो जाता है। मूल रिक्ति के उत्पन्न होने पर, इसे विधिसम्मत भरा जाना अपेक्षित है। इस अपीलार्थी को...
  HYP: 14 अपीलकर्ता को केवल एक अधिमानतः स्थापन की गई हलफनामे में ही नियुक्त किया गया था जो संस्थान में उत्पन्न हुआ था। नियमित नियुक्त किए गए उम्मीदवार की मृत्यु पर, हलफनामे का अस्तित्व समाप्त हो गया। एक बार जब वास्तविक पद का मामला उत्पन्न हुआ,...
- Index 24 | doc=4 | segment=6 | BLEU=12.63 | chrF=39.27
  Evidence: Added legal groups not seen in source/reference: set_aside_quash
  EN: 7 The writ petition filed by the appellant was dismissed by a learned Single Judge of the High Court on 9 October 2013. The appellant filed a Special Appeal against the dismissal of the petition.
  REF: 7. अभ्यर्थी द्वारा दायर रिट याचिका दिनांक 9 अक्टूबर 2013 को माननीय उच्च न्यायालय के विद्गत एकल न्यायाधीश द्वारा निरस्त कर दिया गया। याचिका के निरस्तीकरण के विरुद्ध अपीलार्थी ने विशेष याचिका दायर की।
  HYP: 7. अपीलकर्ता द्वारा दायर रिट याचिका को उच्च न्यायालय द्वारा 9 October 2013 को खारिज कर दिया गया था। अपीलकर्ता ने याचिका को खारिज करने के खिलाफ विशेष अपील दायर की।

### repetition_or_fluency_error

Family: fluency_script | Severity: medium

- Index 43 | doc=21 | segment=7 | BLEU=8.17 | chrF=35.97
  Evidence: Repetition score=0.2887, max token run=2.
  EN: 11. In frivolous or vexatious proceedings, the court owes a duty to look into many other attending circumstances emerging from the record of the case over and above the averments and, if need be, with due care and circumspection try to r...
  REF: 11. बुच्छ या परेशान करने वाली कार्यवाहियों में. न्यायालय का यह कर्तव्य है कि वह मायले के अभिलेख से कथनों के आतिरिक्त अन्य अनेक परिस्थितियों पर भी योर करे ऑर यदि आवश्यक हो तो. पूरी सावधानी ऑर सतर्कता के साथ पंक्तियों के बीच के अर्थ को समझ...
  HYP: 11. अनाधिकृत या षड्यंत्रित कार्यवाही में, न्यायालय को पीड़ितों के साथ उत्पन्न कई अन्य घटनाओं पर गौर करने की जिम्मेदारी है और यदि आवश्यकता है, तो उचित संज्ञान और परिस्थितियों के साथ-साथ लाइन के बीच पढ़ा जाना चाहिए। न्यायालय जब सीआरपीसी की...
- Index 31 | doc=4 | segment=13 | BLEU=3.41 | chrF=38.31
  Evidence: Repetition score=0.3084, max token run=1.
  EN: 14 The appellant was appointed purely on an ad hoc basis in a leave vacancy which arose in the institution. On the death of the regularly appointed candidate, the leave vacancy ceased to exist. Once a substantive vacancy arose, it was re...
  REF: 14. अपीलार्थी को इस संस्थान में रिक्त पद पर पूर्णतः अस्थाई तौर पर नियुक्त किया गया। अस्थाई रूप से अभ्यर्थी की नियुक्ति होते ही रिक्त पद समाप्त हो जाता है। मूल रिक्ति के उत्पन्न होने पर, इसे विधिसम्मत भरा जाना अपेक्षित है। इस अपीलार्थी को...
  HYP: 14 अपीलकर्ता को केवल एक अधिमानतः स्थापन की गई हलफनामे में ही नियुक्त किया गया था जो संस्थान में उत्पन्न हुआ था। नियमित नियुक्त किए गए उम्मीदवार की मृत्यु पर, हलफनामे का अस्तित्व समाप्त हो गया। एक बार जब वास्तविक पद का मामला उत्पन्न हुआ,...
- Index 24 | doc=4 | segment=6 | BLEU=12.63 | chrF=39.27
  Evidence: Repetition score=0.2258, max token run=1.
  EN: 7 The writ petition filed by the appellant was dismissed by a learned Single Judge of the High Court on 9 October 2013. The appellant filed a Special Appeal against the dismissal of the petition.
  REF: 7. अभ्यर्थी द्वारा दायर रिट याचिका दिनांक 9 अक्टूबर 2013 को माननीय उच्च न्यायालय के विद्गत एकल न्यायाधीश द्वारा निरस्त कर दिया गया। याचिका के निरस्तीकरण के विरुद्ध अपीलार्थी ने विशेष याचिका दायर की।
  HYP: 7. अपीलकर्ता द्वारा दायर रिट याचिका को उच्च न्यायालय द्वारा 9 October 2013 को खारिज कर दिया गया था। अपीलकर्ता ने याचिका को खारिज करने के खिलाफ विशेष अपील दायर की।

### named_entity_or_abbreviation_risk

Family: factual_preservation | Severity: medium

- Index 24 | doc=4 | segment=6 | BLEU=12.63 | chrF=39.27
  Evidence: source entity candidates: Single Judge; Special Appeal
  EN: 7 The writ petition filed by the appellant was dismissed by a learned Single Judge of the High Court on 9 October 2013. The appellant filed a Special Appeal against the dismissal of the petition.
  REF: 7. अभ्यर्थी द्वारा दायर रिट याचिका दिनांक 9 अक्टूबर 2013 को माननीय उच्च न्यायालय के विद्गत एकल न्यायाधीश द्वारा निरस्त कर दिया गया। याचिका के निरस्तीकरण के विरुद्ध अपीलार्थी ने विशेष याचिका दायर की।
  HYP: 7. अपीलकर्ता द्वारा दायर रिट याचिका को उच्च न्यायालय द्वारा 9 October 2013 को खारिज कर दिया गया था। अपीलकर्ता ने याचिका को खारिज करने के खिलाफ विशेष अपील दायर की।
- Index 14 | doc=1 | segment=13 | BLEU=15.7 | chrF=41.91
  Evidence: missing abbreviations: PS, SCC | source entity candidates: InJ.K. Synthetics Ltd.; K.P. Agrawal; S. Narasa Goud; Abdul Kareem; Shyam Bihari Lal Gupta
  EN: 11. InJ.K. Synthetics Ltd. v. K.P. Agrawal & Anr.®, this Court dealt with the issue regarding the entitlement of a delinquent to claim continuity of service and consequential benefits in all cases of reinstatement as follows: “17. There...
  REF: 11. जे.के. सिंथेटिक्स लिमिटेड बनाम के.पी अग्रवाल और अन्य* में इस न्यायालय ने सेवा की निरंतरता और बहाली के सभी मामलों में परिणामी लाभों का दावा करने के लिए एक अपराधी के अधिकार के संबंध में मुद्दे को निम्नानुसार निस्तारण किया: "17, यह भी ग...
  HYP: 11. इन्दौर रॉ कॉटन कंपनी बनाम के पी. आर. अग्रवाल और अन्य के मामले में, इस न्यायालय ने निम्नलिखित मामलों में सेवा की परिपक्वता और consequential लाभों का दावा करने के हक सम्बन्धी विवाद पर विचार किया: "17. यह भी एक गलत अवधारणा है कि जब पुनर...
- Index 30 | doc=4 | segment=12 | BLEU=6.05 | chrF=42.72
  Evidence: source entity candidates: Mr. Tanmaya; Senior Counsel; Full Bench; Allahabad High Court; Pramila Mishra
  EN: 13 On the other hand, it has been urged Mr. Tanmaya Agarwal, learned Senior Counsel appearing on behalf of the first respondent that the High Court has correctly come to the conclusion that the ad hoc appointment of the appellant could n...
  REF: 13. दूसरी ओर प्रथम प्रत्यर्थी के वरिष्ठ विद्वान अधिवक्ता श्री न्मय अग्रवाल ने तर्क दिया है कि माननीय उच्च न्यायालय का निष्कर्ष सही है कि अपीलार्थी की तदर्थ नियुक्ति किसी भी परिस्थिति में उस समय के पद धारक की मृत्यु पर मौलिक नियुक्ति नहीं...
  HYP: 13 दूसरी ओर, यह अनुरोध किया गया है कि प्रथम प्रत्यर्थी की ओर से पेश हुए विद्वान वरिष्ठ अधिवक्ता श्री तनन् ्मय अग्रवाल से यह सही ढंग से निर्णय लिया गया है कि अपीलकर्ता की अधिमानतः की गई प्रार्थना पत्र में, किसी भी मामले में, तत्कालीन प्रत...

### date_number_error

Family: factual_preservation | Severity: medium

- Index 14 | doc=1 | segment=13 | BLEU=15.7 | chrF=41.91
  Evidence: Missing dates/numbers from reference: 2, 2003, 212
  EN: 11. InJ.K. Synthetics Ltd. v. K.P. Agrawal & Anr.®, this Court dealt with the issue regarding the entitlement of a delinquent to claim continuity of service and consequential benefits in all cases of reinstatement as follows: “17. There...
  REF: 11. जे.के. सिंथेटिक्स लिमिटेड बनाम के.पी अग्रवाल और अन्य* में इस न्यायालय ने सेवा की निरंतरता और बहाली के सभी मामलों में परिणामी लाभों का दावा करने के लिए एक अपराधी के अधिकार के संबंध में मुद्दे को निम्नानुसार निस्तारण किया: "17, यह भी ग...
  HYP: 11. इन्दौर रॉ कॉटन कंपनी बनाम के पी. आर. अग्रवाल और अन्य के मामले में, इस न्यायालय ने निम्नलिखित मामलों में सेवा की परिपक्वता और consequential लाभों का दावा करने के हक सम्बन्धी विवाद पर विचार किया: "17. यह भी एक गलत अवधारणा है कि जब पुनर...
- Index 30 | doc=4 | segment=12 | BLEU=6.05 | chrF=42.72
  Evidence: Missing dates/numbers from reference: 1284, 1997, 2
  EN: 13 On the other hand, it has been urged Mr. Tanmaya Agarwal, learned Senior Counsel appearing on behalf of the first respondent that the High Court has correctly come to the conclusion that the ad hoc appointment of the appellant could n...
  REF: 13. दूसरी ओर प्रथम प्रत्यर्थी के वरिष्ठ विद्वान अधिवक्ता श्री न्मय अग्रवाल ने तर्क दिया है कि माननीय उच्च न्यायालय का निष्कर्ष सही है कि अपीलार्थी की तदर्थ नियुक्ति किसी भी परिस्थिति में उस समय के पद धारक की मृत्यु पर मौलिक नियुक्ति नहीं...
  HYP: 13 दूसरी ओर, यह अनुरोध किया गया है कि प्रथम प्रत्यर्थी की ओर से पेश हुए विद्वान वरिष्ठ अधिवक्ता श्री तनन् ्मय अग्रवाल से यह सही ढंग से निर्णय लिया गया है कि अपीलकर्ता की अधिमानतः की गई प्रार्थना पत्र में, किसी भी मामले में, तत्कालीन प्रत...
- Index 25 | doc=4 | segment=7 | BLEU=10.43 | chrF=43.59
  Evidence: Missing dates/numbers from reference: 1984
  EN: 8 During the pendency of the Special Appeal, there was an interim order in favour of the appellant in terms similar to the interim protection which was granted earlier on 16 April 1996 by the Single Judge of the High Court. By the impugn...
  REF: 8. विशेष याचिका के लंबन के दौरान अंतरिम इस अंतरिम सुरक्षा के शर्तों की तरह अपीलार्थी के पक्ष में एक अंतरिम आदेश जो कि 16 अप्रैल 1996 के पूर्व माननीय उच्च न्यायालय के एकल न्यायाधीश द्वारा प्रदान की गई। आक्षेपित आदेश दिनांक 30 अक्टूबर 2017...
  HYP: 8. विशेष अपील के लम्बन के दौरान, अपीलकर्ता के पक्ष में आंशिक एवं दीर्घकालिक प्रावधान, जो उच्च न्यायालय के एकमात्र न्यायाधीश द्वारा 16 अप्रैल 1996 को दिया गया था, के संदर्भ में आंशिक प्रावधान था। आक्षेपित आदेश दिनांक 30 October 2017 द्वार...

### format_structure_error

Family: structure | Severity: medium

- Index 14 | doc=1 | segment=13 | BLEU=15.7 | chrF=41.91
  Evidence: list marker count ref=3 hyp=1
  EN: 11. InJ.K. Synthetics Ltd. v. K.P. Agrawal & Anr.®, this Court dealt with the issue regarding the entitlement of a delinquent to claim continuity of service and consequential benefits in all cases of reinstatement as follows: “17. There...
  REF: 11. जे.के. सिंथेटिक्स लिमिटेड बनाम के.पी अग्रवाल और अन्य* में इस न्यायालय ने सेवा की निरंतरता और बहाली के सभी मामलों में परिणामी लाभों का दावा करने के लिए एक अपराधी के अधिकार के संबंध में मुद्दे को निम्नानुसार निस्तारण किया: "17, यह भी ग...
  HYP: 11. इन्दौर रॉ कॉटन कंपनी बनाम के पी. आर. अग्रवाल और अन्य के मामले में, इस न्यायालय ने निम्नलिखित मामलों में सेवा की परिपक्वता और consequential लाभों का दावा करने के हक सम्बन्धी विवाद पर विचार किया: "17. यह भी एक गलत अवधारणा है कि जब पुनर...

### outcome_error

Family: legal_domain_fidelity | Severity: high

- Index 25 | doc=4 | segment=7 | BLEU=10.43 | chrF=43.59
  Evidence: Missing legal-outcome groups: allowed_relief
  EN: 8 During the pendency of the Special Appeal, there was an interim order in favour of the appellant in terms similar to the interim protection which was granted earlier on 16 April 1996 by the Single Judge of the High Court. By the impugn...
  REF: 8. विशेष याचिका के लंबन के दौरान अंतरिम इस अंतरिम सुरक्षा के शर्तों की तरह अपीलार्थी के पक्ष में एक अंतरिम आदेश जो कि 16 अप्रैल 1996 के पूर्व माननीय उच्च न्यायालय के एकल न्यायाधीश द्वारा प्रदान की गई। आक्षेपित आदेश दिनांक 30 अक्टूबर 2017...
  HYP: 8. विशेष अपील के लम्बन के दौरान, अपीलकर्ता के पक्ष में आंशिक एवं दीर्घकालिक प्रावधान, जो उच्च न्यायालय के एकमात्र न्यायाधीश द्वारा 16 अप्रैल 1996 को दिया गया था, के संदर्भ में आंशिक प्रावधान था। आक्षेपित आदेश दिनांक 30 October 2017 द्वार...
- Index 12 | doc=1 | segment=11 | BLEU=13.36 | chrF=46.86
  Evidence: Missing legal-outcome groups: dismissal_rejection
  EN: 9. Mr. Rajesh Kumar-l, learned counsel appearing for the Bank submitted that the Appellant was not exonerated on the charge. The Disciplinary Authority merely reduced the penalty from dismissal to reduction in time scale of pay which doe...
  REF: 9. बैंक के लिए उपस्थित विद्गत अधिवक्ता श्री राजेश कुमार- ने प्रस्तुत किया कि अपीलकर्ता को आरोप से बरी नहीं किया गया था। अनुशासनात्मक प्राधिकरण ने केवल वेतन के समय मान में कमी करने के लिए बर्खास्तगी से जुमनि को कम कर दिया गया था, जो अपीलक...
  HYP: 9. श्री राजेश कुमार ने बैंक की ओर से प्रस्तुत विद्वान अधिवक्ता ने कहा कि अपीलकर्ता आरोप पर निर्मुक्त नहीं था। प्रशिक्षु प्राधिकारी ने केवल जमानत की अवधि से अवकाश तक की अवधि के माप से आक्षेपित किया, जो अपीलकर्ता को निलम्बन की अवधि के दौरा...
- Index 15 | doc=1 | segment=14 | BLEU=28.02 | chrF=49.08
  Evidence: Missing legal-outcome groups: conviction_sentence
  EN: 12. It was further held in the said judgment that if reinstatement is a consequence of imposition of a lesser punishment, neither back-wages nor continuity of service nor consequential benefits follow as a natural or necessary consequenc...
  REF: 12. उक्त निर्णय में आगे कहा गया कि यदि बहाली कम सजा देने का परिणाम है, तो न तो पूर्व भत्ता और न ही सेवा की निरंतरता और न ही परिणामी लाभ इस तरह की बहाली के प्राकृतिक या आवश्यक परिणाम के रूप में पालन किया जाना चाहिए। उक्ता न्यायालय यह अवधा...
  HYP: 12. उक्त निर्णय में यह भी अवारिरतित किया गया कि यदि पुनर्मिलान एक कम्युनिक प्रभाव का परिणाम है, तो सेवा के नियोजित या आवश्यक परिणाम के रूप में इस तरह के पुनर्मिलान के लिए कोई लागत नहीं आती है। इस न्यायालय ने आगे कहा कि जहां तक अभिलेख को...

### wrong_script_or_source_copying

Family: fluency_script | Severity: critical

- Index 26 | doc=4 | segment=8 | BLEU=17.94 | chrF=46.07
  Evidence: Hypothesis script/copying signal: Latin ratio=0.0961, Devanagari ratio=0.8609, copied Latin terms=6.
  EN: 9 From the order of the High Court, it emerges that a counter affidavit was filed in the course of the Special Appeal where it was stated on behalf of the DIOS that by a letter dated 14 July 1994, approval for the appointment of the appe...
  REF: 9. माननीय उच्च न्यायालय के आदेश से यह प्रतीत होता है कि प्रति शपथपत्र दायर किया गया जिसमें डीआईओएस की तरफ से यह कहा गया कि दिनांक 14 जुलाई 1994 को पत्र के माध्यम से प्रत्यर्थी की नियुक्ति के अनुमोदन को मना कर दिया गया था क्योंकि यह आदेश...
  HYP: 9. उच्च न्यायालय के आदेश से, यह पता चलता है कि विशेष अपील के दौरान एक जवाबी हलफनामा दायर किया गया था, जिसमें डीIOS की ओर से कहा गया था कि दिनांक 14 July 1994 के एक पत्र द्वारा अपीलकर्ता की नियुक्ति को मंजूरी नहीं दी गई थी क्योंकि यह यूपी...
- Index 7 | doc=1 | segment=6 | BLEU=27.72 | chrF=55.7
  Evidence: Hypothesis script/copying signal: Latin ratio=0.0346, Devanagari ratio=0.934, copied Latin terms=5.
  EN: 4. The Appellant filed a Writ Petition challenging the order of dismissal which was not entertained by the High Court. Liberty was given to the Appellant to file an appeal. Pursuant to the liberty granted by the High Court, the Appellant...
  REF: 4. अपीलकर्ता ने बर्खास्तगी के आदेश को चुनौती देते हुए एक रिट याचिका दायर की, जिस पर उच्च न्यायालय द्वारा विचार नहीं किया गया था। अपीलकर्ता को अपील दायर करने के लिए स्वतंत्रता दी गई थी। उच्च न्यायालय द्वारा दी गई स्वतंत्रता के अनुसार, अपी...
  HYP: 4. अपीलकर्ता ने एक रिट याचिका दायर की जिस पर उच्च न्यायालय ने विचार नहीं किया था। अपीलकर्ता को एक अपील दायर करने की स्वतंत्रता दी गई थी। उच्च न्यायालय द्वारा स्वतंत्रता प्रदान की गई इस स्वतंत्रता के अनुरूप, अपीलकर्ता ने अनुशासनात्मक प्रा...
- Index 45 | doc=21 | segment=9 | BLEU=23.21 | chrF=56.01
  Evidence: Hypothesis script/copying signal: Latin ratio=0.0282, Devanagari ratio=0.931, copied Latin terms=6.
  EN: 17. This Court in the case of Arun Jain (supra) has also taken a similar view, and in exercise of powers under Article 142 of the Constitution of India, set aside the criminal complaint, FIR and all other criminal proceedings. The operat...
  REF: 17. इस न्यायालय ने अरुण जैन (उपरोक्त) के मामले में भी ऐसा ही दृष्टिकोण अपनाया है, तथा भारत के संविधान के अनुच्छेद 142 के तहत शक्तियों का प्रयोग करते हुए, आपराधिक शिकायत, एफआईआर तथा अन्य सभी आपराधिक कार्यवाही को रद्द कर दिया है। उक्त मामल...
  HYP: 17. इस न्यायालय ने सुश्री तनु (उपरोक्त मामले में) के मामले में भी इसका इसी तरह का दृष्टिकोण लिया है, और भारत के संविधान के अनुच्छेद 142 के तहत शक्तियों का प्रयोग करते हुए आपराधिक शिकायत, एफआईआर और अन्य आपराधिक कार्यवाही को अपास्त कर दिया...

### party_role_error

Family: legal_domain_fidelity | Severity: high

- Index 5 | doc=1 | segment=4 | BLEU=22.78 | chrF=53.31
  Evidence: Missing party-role groups: accused_party
  EN: 2. Yet another charge sheet was issued on 30.05.2003 in which the following charges were framed: i. You have violated discipline of bank. li. You are accused of misconduct. lili. You have made effort to diffuse the Bank image and on the...
  REF: 2. फिर भी 30.05.2003 को एक और आरोप पत्र जारी किया गया जिसमें निम्नलिखित आरोप लगाए गए थे: i. आपने बैंक के अनुशासन का उल्लंघन किया है। ii. आप पर कदाचार का आरोपी है। iii. आपने बैंक की छवि को बिगाड़ने का प्रयास किया है और इसके आधार पर आपने द...
  HYP: 2. दिनांक 30.05.2003 को एक और आरोप पत्र जारी किया गया था जिसमें निम्नलिखित आरोपों को छा गया था: i. आप ने बैंक के नियमों का पालन नहीं किया है। इन्। आप भ्रष्टाचार के आरोप में हैं। lili. आप ने बैंक की 이미지 को व्यापक रूप से प्रस्तुत करने के ल...
- Index 45 | doc=21 | segment=9 | BLEU=23.21 | chrF=56.01
  Evidence: Missing party-role groups: accused_party
  EN: 17. This Court in the case of Arun Jain (supra) has also taken a similar view, and in exercise of powers under Article 142 of the Constitution of India, set aside the criminal complaint, FIR and all other criminal proceedings. The operat...
  REF: 17. इस न्यायालय ने अरुण जैन (उपरोक्त) के मामले में भी ऐसा ही दृष्टिकोण अपनाया है, तथा भारत के संविधान के अनुच्छेद 142 के तहत शक्तियों का प्रयोग करते हुए, आपराधिक शिकायत, एफआईआर तथा अन्य सभी आपराधिक कार्यवाही को रद्द कर दिया है। उक्त मामल...
  HYP: 17. इस न्यायालय ने सुश्री तनु (उपरोक्त मामले में) के मामले में भी इसका इसी तरह का दृष्टिकोण लिया है, और भारत के संविधान के अनुच्छेद 142 के तहत शक्तियों का प्रयोग करते हुए आपराधिक शिकायत, एफआईआर और अन्य आपराधिक कार्यवाही को अपास्त कर दिया...
- Index 10 | doc=1 | segment=9 | BLEU=41.47 | chrF=71.9
  Evidence: Missing party-role groups: respondent_party
  EN: 7. Notice was issued to the Respondent by this Court to show cause as to why the Appellant shall not be entitled for salary for the period of suspension from 29.07.2003 to 10.09.2012.
  REF: 7. इस न्यायालय द्वारा प्रत्यर्थी को कारण बताओ नोटिस जारी किया गया था कि अपीलकर्ता को 29.07.2003 से 10.09.2012 तक निलंबन की अवधि के लिए वेतन का हकदार क्‍यों नहीं होगा।
  HYP: 7. प्रत्यर्थी को इस न्यायालय द्वारा कारण बताओ नोटिस जारी किया गया था कि अपीलकर्ता दिनांक 29.07.2003 से 10.09.2012 के अवधि के लिए अनुतोषी के हकदार नहीं होगा।

### statutory_reference_error

Family: legal_domain_fidelity | Severity: high

- Index 7 | doc=1 | segment=6 | BLEU=27.72 | chrF=55.7
  Evidence: Missing statutory groups/refs: statutory_reference
  EN: 4. The Appellant filed a Writ Petition challenging the order of dismissal which was not entertained by the High Court. Liberty was given to the Appellant to file an appeal. Pursuant to the liberty granted by the High Court, the Appellant...
  REF: 4. अपीलकर्ता ने बर्खास्तगी के आदेश को चुनौती देते हुए एक रिट याचिका दायर की, जिस पर उच्च न्यायालय द्वारा विचार नहीं किया गया था। अपीलकर्ता को अपील दायर करने के लिए स्वतंत्रता दी गई थी। उच्च न्यायालय द्वारा दी गई स्वतंत्रता के अनुसार, अपी...
  HYP: 4. अपीलकर्ता ने एक रिट याचिका दायर की जिस पर उच्च न्यायालय ने विचार नहीं किया था। अपीलकर्ता को एक अपील दायर करने की स्वतंत्रता दी गई थी। उच्च न्यायालय द्वारा स्वतंत्रता प्रदान की गई इस स्वतंत्रता के अनुरूप, अपीलकर्ता ने अनुशासनात्मक प्रा...
- Index 38 | doc=21 | segment=2 | BLEU=23.92 | chrF=58.34
  Evidence: Missing statutory groups/refs: 482
  EN: 6. Learned counsel appearing for the Appellants has vehemently argued before this Court that Appellant No. 3 filed a matrimonial case on 17.06.2021 and the said FIR was lodged only as a counter blast on 19.08.2021 in order to harass and...
  REF: 6. अपीलकर्ताओं की ओर से उपस्थित विद्वान अधिवक्ता ने इस न्यायालय के समक्ष पुरजोर तर्क दिया है कि अपीलकर्ता संख्या 3 ने दिनांक 17.06.2021 को एक वैवाहिक मामला दायर किया था और उक्त एफआईआर केवल 19.08.2021 को एक जवाबी विरोध के रूप में दर्ज की...
  HYP: 6. अपीलकर्ताओं की तरफ से उपस्थित विद्वान अधिवक्ता ने जोरदार ढंग से न्यायालय के समक्ष यह तर्क दिया कि अपीलकर्ता संख्या 3 ने 17.06.2021 को एक वैवाहिक मामला दायर किया था और उक्त प्राथमिकी केवल 19.08.2021 को ही पूरे परिवार को अपमानित और अपमा...
- Index 6 | doc=1 | segment=5 | BLEU=37.82 | chrF=66.78
  Evidence: Missing statutory groups/refs: statutory_reference
  EN: 3. The Appellant submitted his reply to the said charge sheets dated 27.05.2003 and 30.05.2003. The Appellant was placed under suspension by an order dated 29.07.2003. He challenged the order of suspension by filing a Writ Petition which...
  REF: 3. अपीलार्थी ने उक्त आरोप पत्र दिनांक 27.05.2003 और 30.05.2003 को अपना जवाब प्रस्तुत किया। अपीलार्थी को 29.07.2003 के एक आदेश द्वारा निलंबन किया गया था। उन्होंने रिट याचिका दायर करके निलंबन के आदेश को चुनौती दी, जिसके द्वारा बैंक को चार...
  HYP: 3. अपीलकर्ता ने उक्त आरोप पत्रों दिनांक 27.05.2003 और 30.05.2003 के प्रस्तुतियों पर अपना उत्तर दिया। अपीलकर्ता को एक आदेश दिनांक 29.07.2003 द्वारा निलम्बित कर दिया गया था। उसने एक रिट याचिका दायर करके निलम्बन के आदेश को चुनौती दी, जिस पर...

### over_translation_addition

Family: adequacy | Severity: high

- Index 38 | doc=21 | segment=2 | BLEU=23.92 | chrF=58.34
  Evidence: Length ratio=1.6203; hypothesis is much longer than reference.
  EN: 6. Learned counsel appearing for the Appellants has vehemently argued before this Court that Appellant No. 3 filed a matrimonial case on 17.06.2021 and the said FIR was lodged only as a counter blast on 19.08.2021 in order to harass and...
  REF: 6. अपीलकर्ताओं की ओर से उपस्थित विद्वान अधिवक्ता ने इस न्यायालय के समक्ष पुरजोर तर्क दिया है कि अपीलकर्ता संख्या 3 ने दिनांक 17.06.2021 को एक वैवाहिक मामला दायर किया था और उक्त एफआईआर केवल 19.08.2021 को एक जवाबी विरोध के रूप में दर्ज की...
  HYP: 6. अपीलकर्ताओं की तरफ से उपस्थित विद्वान अधिवक्ता ने जोरदार ढंग से न्यायालय के समक्ष यह तर्क दिया कि अपीलकर्ता संख्या 3 ने 17.06.2021 को एक वैवाहिक मामला दायर किया था और उक्त प्राथमिकी केवल 19.08.2021 को ही पूरे परिवार को अपमानित और अपमा...
