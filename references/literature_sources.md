# Literature Sources To Track

This file tracks candidate sources for primary data extraction. The current seed dataset is only for pipeline testing and must be checked against primary literature before final use.

## Priority primary sources

- Agard, Baskin, Prescher, Lo, Bertozzi. "A comparative study of bioorthogonal reactions with azides." ACS Chemical Biology, 2006. DOI: `10.1021/cb6003228`.
- Baskin, Prescher, Laughlin, Agard, Chang, Miller, Lo, Codelli, Bertozzi. "Copper-free click chemistry for dynamic in vivo imaging." PNAS, 2007. Candidate DOI: `10.1073/pnas.0707090104`.
- Codelli, Baskin, Agard, Bertozzi. "Second-generation difluorinated cyclooctynes for copper-free click chemistry." JACS, 2008. Candidate DOI needs verification.
- Jewett, Sletten, Bertozzi. "Rapid Cu-Free Click Chemistry with Readily Synthesized Biarylazacyclooctynones." JACS, 2010. Candidate DOI needs verification.
- Sletten, Bertozzi. "A Hydrophilic Azacyclooctyne for Cu-Free Click Chemistry." Organic Letters, 2008 or 2009. Candidate DOI needs verification.
- Rostovtsev, Green, Fokin, Sharpless. "A Stepwise Huisgen Cycloaddition Process: Copper(I)-Catalyzed Regioselective Ligation of Azides and Terminal Alkynes." Angewandte Chemie International Edition, 2002. Use for CuAAC mechanism and conditions, not necessarily directly comparable kinetics.
- Tornoe, Christensen, Meldal. "Peptidotriazoles on Solid Phase: [1,2,3]-Triazoles by Regiospecific Copper(I)-Catalyzed 1,3-Dipolar Cycloadditions of Terminal Alkynes to Azides." Journal of Organic Chemistry, 2002. Use for CuAAC origin and conditions.

## Extraction checklist

- Record exact azide and alkyne partner.
- Record solvent, temperature, pH, catalyst, and concentration if reported.
- Copy the unit exactly, then add normalized values only after checking dimensional consistency.
- Mark each row as `primary_checked` only after the value is confirmed from the paper table, figure, or supplementary information.
- Do not combine rates measured under different conditions without adding the caveat in `notes`.

## Additional papers to inspect for more `k_value` rows

These are not part of the original priority set. They are selected because they are likely to contain SPAAC/CuAAC kinetic measurements, second-order rate constants, or directly comparable reaction-rate data. Inspect the main text and SI before entering rows.

### Highest priority: likely experimental SPAAC rate constants

- Jan Dommerholt, Samuel Schmidt, Rinske Temming, Linda J. A. Hendriks, Floris P. J. M. Rutjes, et al. "Readily Accessible Bicyclononynes for Bioorthogonal Labeling and Three-Dimensional Imaging of Living Cells." Angewandte Chemie International Edition. Target: BCN/bicyclononyne azide rate constants.
- Ngalle E. Mbua, Jun Guo, Margreet A. Wolfert, Richard Steet, Geert-Jan Boons. "Strain-Promoted Alkyne-Azide Cycloadditions (SPAAC) Reveal New Features of Glycoconjugate Biosynthesis." ChemBioChem. Target: DIBO/related cyclooctyne rate constants and cell-labeling conditions.
- John C. Jewett, Carolyn R. Bertozzi. "Synthesis of a fluorogenic cyclooctyne activated by Cu-free click chemistry." Organic Letters. Target: fluorogenic cyclooctyne/coumarin cyclooctyne kinetics.
- Andrei A. Poloukhtine, Ngalle E. Mbua, Margreet A. Wolfert, Geert-Jan Boons, Vladimir V. Popik. "Selective Labeling of Living Cells by a Photo-Triggered Click Reaction." Journal of the American Chemical Society. Target: photoactivated cyclooctyne azide rates.
- Richard D. Carpenter, Sven H. Hausner, Julie L. Sutcliffe. "Copper-Free Click for PET: Rapid 1,3-Dipolar Cycloadditions with a Fluorine-18 Cyclooctyne." ACS Medicinal Chemistry Letters. Target: radiolabeled fluorocyclooctyne SPAAC rates.
- Jan Dommerholt / Floris Rutjes group papers on BCN derivatives after the first BCN report. Search exact terms: `BCN azide rate constant`, `bicyclononyne SPAAC kinetics`, `endo-BCN exo-BCN azide rate`.
- Sander S. van Berkel, Anton J. Dirks, Floris L. van Delft, et al. papers on `DIBAC` / `ADIBO` / `aza-dibenzocyclooctyne`. Target: DIBAC or ADIBO second-order rate constants.
- Tilman Plass, Sigrid Milles, Christine Koehler, Carsten Schultz, Edward A. Lemke. "Genetically Encoded Copper-Free Click Chemistry." Angewandte Chemie International Edition. Target: genetically encoded strained alkyne or cyclooctyne reaction rates with azides.
- Anne B. Neef, Carsten Schultz. "Selective Fluorescence Labeling of Lipids in Living Cells." Angewandte Chemie International Edition. Target: cyclooctyne lipid-labeling probe kinetics.

### Medium priority: useful for mechanism or activation-energy interpretation

- Daniel H. Ess, Gavin O. Jones, K. N. Houk. "Transition States of Strain-Promoted Metal-Free Click Chemistry: 1,3-Dipolar Cycloadditions of Phenyl Azide and Cyclooctynes." Organic Letters. Target: computed activation barriers/descriptors, not necessarily experimental `k`.
- Franziska Schoenebeck, Daniel H. Ess, Gavin O. Jones, K. N. Houk. "Reactivity and Regioselectivity in 1,3-Dipolar Cycloadditions of Azides to Strained Alkynes and Alkenes: A Computational Study." Journal of the American Chemical Society. Target: computed barriers and regioselectivity descriptors.
- Kimberly Chenoweth, David Chenoweth, William A. Goddard III. "Cyclooctyne-based reagents for uncatalyzed click chemistry: A computational survey." Organic & Biomolecular Chemistry. Target: descriptor/barrier support for cyclooctyne structural features.

### CuAAC kinetics and mechanism candidates

- "Ligand-Accelerated Cu-Catalyzed Azide-Alkyne Cycloaddition: A Mechanistic Report." Journal of the American Chemical Society. Target: ligand-dependent CuAAC rate/kinetic data.
- Valentin O. Rodionov, Valery V. Fokin, M. G. Finn. "Mechanism of the Ligand-Free CuI-Catalyzed Azide-Alkyne Cycloaddition Reaction." Angewandte Chemie International Edition. Target: CuAAC kinetic/mechanistic data.
- B. T. Worrell, J. A. Malik, V. V. Fokin. "Direct Evidence of a Dinuclear Copper Intermediate in Cu(I)-Catalyzed Azide-Alkyne Cycloadditions." Science. Target: mechanism support; use for kinetics only if usable rate data appears in main text or SI.

### Practical extraction notes for the next pass

- Prioritize papers that report `M^-1 s^-1` second-order rate constants. Add these rows first.
- Do not spend much time on papers that only report imaging success, fluorescence turn-on, or yield without `k`.
- For computational papers, fill `Ea_kJ_mol` only if the paper reports a barrier that can be defensibly treated as an activation barrier; otherwise keep it as interpretation-only in `notes`.
- Keep SPAAC and CuAAC rows separate during analysis. They are mechanistically different and should not be forced into one prediction task unless the report explicitly frames it as coarse exploratory comparison.
