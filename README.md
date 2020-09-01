# pyCamillaDSP_plot
Companion Python library for plotting configurations and filters for CamillaDSP. It is also used by the web interface.

Install with 
```sh
pip install .
```

## Plotting a configuration
This library provides the console command `plotcamillaconf`. Once the library is installed, the command should be available in your terminal.
To use it type:
```sh
plotcamillaconf /path/to/some/config.yml
```

This will plot the frequency response of all the defined filters, and show a block diagram of the pipeline.


## Evaluating filters
To plot the frequency response of a filter, use the function `plot_filter`. This is mostly meant for internal use by the `plotcamillaconf` command.
```python
plot_filter(filterconf, name=None, samplerate=44100, npoints=1000, toimage=False)
```
This will plot using PyPlot. The filter configuration `filterconf` must be provided. The `samplerate` defaults to 44100 if not given. The filter `name` is used for labels. The number of points in the plot is set with `npoints`. If `toimage` is set to True, then it will instead return the plot as an svg image.

It's also possible to plot the combined frequency response of a Filter step in the pipeline.
```python
plot_filterstep(conf, pipelineindex, name="filterstep", npoints=1000, toimage=False)
```
This command takes the full configuration as `conf` must be provided. This will plot the step with index `pipelineindex` in the pipeline where 0 is the first step. The `name` is used for the plot title. The number of points in the plot is set with `npoints`. If `toimage` is set to True, then it will instead return the plot as an svg image.

## Plotting the pipeline
To plot a block diagram of the pipeline, use the function `plot_pipeline`. This is mostly meant for internal use by the `plotcamillaconf` command.
```python
plot_pipeline(conf, toimage=False)
```
This takes a full CamillaDSP configuration, `conf`. It will then plot the pipeline using PyPlot. If `toimage` is set to True, then it will instead return the plot as an svg image.

