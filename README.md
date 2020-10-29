# pyCamillaDSP_plot
Companion Python library for plotting configurations and filters for CamillaDSP. It is also used by the web interface.

Download the library, either by `git clone` or by downloading a zip file of the code. Then unpack the files, go to the folder containing the `setup.py` file and run: 
```sh
pip install .
```
Note that on some systems the command is `pip3` instead of `pip`.

## Requirements
This library requires Python 3.6 or newer. For plotting configurations with the commandline tool `plotcamillaconf`, it also requires `numpy` and `matplotlib`. These are not required for using only with the web interface.

These are the names of the packages needed:
| Distribution | python | numpy (optional) | matplotlib (optional) |
|--------------|--------|-------|------------|
| Fedora | python3 | python3-numpy | python3-matplotlib |
| Debian/Raspbian | python3 | python3-numpy | python3-matplotlib |
| Arch | python | python-numpy | python-matplotlib |
| pip | - | numpy | matplotlib | 
| Anaconda | - | numpy | matplotlib |

### Linux
Most linux distributions have Python 3.6 or newer installed by default. Use the normal package manager to install the packages.

### Windows
Use Anaconda: https://www.anaconda.com/products/individual. Then use Anaconda Navigator to install the dependencies.

### macOS
On macOS use either Anaconda or Homebrew. The Anaconda procedure is the same as for Windows. 

For Homebrew, install Python with `brew install python`, after which you can install the needed packages with pip, `pip3 install numpy` etc.




## Plotting a configuration from the command line
This library provides the console command `plotcamillaconf`. Once the library is installed, togehter with the optional dependencies numpy and matplotlib, the command should be available in your terminal.
To use it type:
```sh
plotcamillaconf /path/to/some/config.yml
```

This will plot the frequency response of all the defined filters, and show a block diagram of the pipeline.


## Plotting filters
To plot the frequency response of a filter, use the function `plot_filter`. This is mostly meant for internal use by the `plotcamillaconf` command.
```python
plot_filter(filterconf, name=None, samplerate=44100, npoints=1000, toimage=False)
```
This will plot using PyPlot. The filter configuration `filterconf` must be provided. The `samplerate` defaults to 44100 if not given. The filter `name` is used for labels. The number of points in the plot is set with `npoints`. If `toimage` is set to True, then it will instead return the plot as an svg image.

It's also possible to plot the combined frequency response of a Filter step in the pipeline.
```python
plot_filterstep(conf, pipelineindex, name="filterstep", npoints=1000, toimage=False)
```
This command takes a full configuration as `conf`. It will then plot the step with index `pipelineindex` in the pipeline where 0 is the first step. The `name` is used for the plot title. The number of points in the plot is set with `npoints`. If `toimage` is set to True, then it will instead return the plot as an svg image.

## Plotting the pipeline
To plot a block diagram of the pipeline, use the function `plot_pipeline`. This is mostly meant for internal use by the `plotcamillaconf` command.
```python
plot_pipeline(conf, toimage=False)
```
This takes a full CamillaDSP configuration, `conf`. It will then plot the pipeline using PyPlot. If `toimage` is set to True, then it will instead return the plot as an svg image.

## Evaluating filters
To evaluate the frequency response of a filter, use the function `eval_filter`. This is mostly meant for internal use by the `plotcamillaconf` command as well as the web gui.
```python
eval_filter(filterconf, name=None, samplerate=44100, npoints=1000)
```
This will evaluate the filter and return the result as a dictionary. The filter configuration `filterconf` must be provided. The `samplerate` defaults to 44100 if not given. The filter `name` is used for labels. The number of points in the plot is set with `npoints`. The contents of the returned dictionary depends on the filter type. A Biquad returns `name`, `samplerate`, `f`, `magnitude` and `phase`. A Conv filter additionally return the impulse response in `time` and `impulse`.

It's also possible to evaluate the combined frequency response of a Filter step in the pipeline.
```python
eval_filterstep(conf, pipelineindex, name="filterstep", npoints=1000)
```
This command takes a full configuration as `conf`. It will evaluate the step with index `pipelineindex` in the pipeline where 0 is the first step. As for eval_filter, the result is returned as a dictionary with the same fields as for a Biquad.

