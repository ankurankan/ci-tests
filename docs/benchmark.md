# Benchmark

:::{only} sweep

```{raw} html
<div class="sweep-chart" data-src="sweep.json"></div>
<noscript><p>Turn on JavaScript to see the chart, or read the <a href="https://github.com/pgmpy/FastCIT/blob/main/benchmarks/results/sweep.md">sweep tables</a>.</p></noscript>
```

:::

:::{only} not sweep

The benchmark results are not available at this time.

:::

## Method

The page lists the computer and the package versions with the results.
The sample size goes from 100 to 100 000 (HSIC and KCI: to 2 000), and |Z| goes from 0 to 8.
Each point times 20 queries (HSIC and KCI: 10) in 3 passes, and each query keeps its fastest pass.
The result is the median time of one call over these queries.
When the first pass at a point takes more than 60 s, the package skips the larger points.
The [benchmark README](https://github.com/pgmpy/FastCIT/blob/main/benchmarks/README.md) gives the full method.
