# Analysis Summary

- Rows used: 26
- Projection method: sklearn
- Cluster method: spectral_clustering
- Ridge leave-one-out RMSE on log10(k): 0.581
- Data warning: results are exploratory until analysis rows are primary-checked and measured under comparable conditions.

## Top feature correlations

| feature | abs_corr_with_log10_k |
| --- | --- |
| alkyne_family_cyclooctyne | 0.7833532945355113 |
| fused_aromatic_count_missing | 0.7198715162798218 |
| alkyne_family_biarylazacyclooctynone | 0.38481198362198543 |
| alkyne_family_bicyclononyne | 0.3716379667743822 |
| solvent_class_mixed | 0.326948260739627 |

## Cluster assignments

| record_id | alkyne | cluster | rate_label | log10_k |
| --- | --- | --- | --- | --- |
| rec001 | cyclooctyne compound 12 | spectral_cluster_2 |  | -2.3665315444204134 |
| rec002 | free acid of cyclooctyne compound 1 | spectral_cluster_2 |  | -2.619788758288394 |
| rec003 | cyclooctyne compound 8 | spectral_cluster_2 |  | -2.886056647693163 |
| rec004 | cyclooctyne compound 13 | spectral_cluster_2 |  | -2.9208187539523753 |
| rec005 | DIFO | spectral_cluster_0 |  | -1.1191864077192086 |
| rec006 | 6,7-dimethoxyazacyclooct-4-yne (DIMAC) | spectral_cluster_0 |  | -2.5228787452803374 |
| rec007 | second-generation DIFO compound 2 | spectral_cluster_0 |  | -1.3767507096020994 |
| rec008 | second-generation DIFO compound 3 | spectral_cluster_0 |  | -1.2839966563652008 |
| rec009 | second-generation DIFO compound 2 | spectral_cluster_0 |  | -1.0457574905606752 |
| rec010 | second-generation DIFO compound 3 | spectral_cluster_0 |  | -1.0655015487564323 |
| rec011 | BARAC derivative 15 | spectral_cluster_1 |  | -0.017728766960431602 |
| rec063 | endo-6 (bicyclo[6.1.0]non-4-yn-9-ol) | spectral_cluster_0 |  | -0.8538719643217619 |
| rec064 | exo-6 (bicyclo[6.1.0]non-4-yn-9-ol) | spectral_cluster_0 |  | -0.958607314841775 |
| rec065 | endo-6 (bicyclo[6.1.0]non-4-yn-9-ol) | spectral_cluster_0 |  | -0.5376020021010439 |
| rec066 | exo-6 (bicyclo[6.1.0]non-4-yn-9-ol) | spectral_cluster_0 |  | -0.721246399047171 |
| rec067 | 1a (11,12-didehydro-5,6-dihydro-dibenzo[a,e]cycloocten-5-ol; DIBO) | spectral_cluster_1 |  | -1.2464169411070933 |
| rec068 | 3c (photogenerated 4,9-dibutoxy dibenzocyclooctyne) | spectral_cluster_1 |  | -1.1174754620451195 |
| rec069 | 3c (photogenerated 4,9-dibutoxy dibenzocyclooctyne) | spectral_cluster_1 |  | -1.2321023839819094 |
| rec070 | 3c (photogenerated 4,9-dibutoxy dibenzocyclooctyne) | spectral_cluster_1 |  | -1.4647058799572295 |
| rec071 | 3c (photogenerated 4,9-dibutoxy dibenzocyclooctyne) | spectral_cluster_1 |  | -1.7878123955960423 |
| rec072 | 3c (photogenerated 4,9-dibutoxy dibenzocyclooctyne) | spectral_cluster_1 |  | -1.3555614105321614 |
| rec073 | 12 | spectral_cluster_1 |  | -1.408935392973501 |
| rec074 | 3 (4-dibenzocyclooctynol; DIBO) | spectral_cluster_1 |  | -1.2464169411070933 |
| rec075 | 9 (DIBO carbamate) | spectral_cluster_1 |  | -1.157390760389438 |
| rec076 | 11 (DIBO ketone) | spectral_cluster_1 |  | -0.5867002359187482 |
| rec077 | 12 (DIBO oxime) | spectral_cluster_1 |  | -1.2139587897574458 |