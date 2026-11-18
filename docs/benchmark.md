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
The sample size goes from 100 to 100 000 (HSIC and KCI: to 10 000), and |Z| goes from 0 to 8.
Each point runs 20 queries (HSIC and KCI: 10) one time, and the first call is only a warm-up call.
The result is the mean time of the other calls, with its standard error.
When a point takes more than 60 s, the package skips the larger points.
The [benchmark README](https://github.com/pgmpy/FastCIT/blob/main/benchmarks/README.md) gives the full method.
