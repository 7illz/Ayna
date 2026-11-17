# Try-on blockers

This file records optional or private inputs that are intentionally not downloaded or committed.

## Part A tattoo regression fixture

- Missing item: the authorized bare-arm person photograph and short-sleeve polo garment named in
  the task. No concrete path was supplied and `.data/fixtures/` is absent.
- Required placement: any private paths below `.data/fixtures/`; set
  `AYNA_TRYON_TATTOO_PERSON` and `AYNA_TRYON_TATTOO_GARMENT` to those files.
- Size: user-supplied image files; unknown until supplied.
- License/consent: the operator must have consent and authorization for local evaluation. Images
  remain Git-ignored and must not be committed.
- Effect: the three-seed tattoo diagnosis and opt-in GPU regression cannot run. The test skips
  honestly; the existing authorized long-sleeve-to-short-sleeve pair was used only for the
  measured original-resolution/CUDA check.
