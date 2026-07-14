# Taylor diagrams

Read this file only for Taylor-diagram requests or when a model-comparison task is
being evaluated for a Taylor representation.

## Scientific contract

Use a Taylor diagram only when the audience expects it and the inputs are explicit:

- correlation with the observation/reference series;
- raw or normalized standard deviation;
- centered RMSE when represented by contours or distance;
- one consistent reference dataset and sample support across compared models.

Label whether standard deviation is normalized and identify the reference value.
Do not mix correlation, bias, uncentered RMSE, or unequal validation samples without
clear explanation. A Taylor diagram does not display mean bias by itself.

If target readers are unlikely to know the geometry, use separate correlation, RMSE,
bias, and spread panels or move the Taylor diagram to supplementary material.

## Layout and guides

Keep model markers distinguishable through an accessible cycle and redundant marker
shape when needed. Avoid crowding model labels inside the data region; prefer a
verified external legend. Preserve UltraPlot auto-layout on the first render and
measure the final canvas after all guides and RMSE contours are drawn.

## Submission QA

- the reference series, sample unit, and period are stated;
- correlation and standard-deviation inputs are computed on matched observations;
- normalized versus raw spread and centered RMSE are labeled correctly;
- model markers and legend entries map one-to-one and remain readable at final size;
- any complementary bias information is shown elsewhere or explicitly reported absent;
- final size, fonts, guide geometry, and saved artifacts pass the target policy.
