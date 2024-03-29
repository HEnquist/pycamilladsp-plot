# pyCamillaDSP_plot
Companion Python library for plotting configurations and filters for CamillaDSP. It is also used by the web interface.

## Installation
### Requirements
This library requires Python 3.8 or newer. For plotting configurations with the commandline tool `plotcamillaconf`, it also requires `numpy` and `matplotlib`. These are not required for using only with the web interface, but if `numpy` is available it will be used to speed up evaluation of FIR filters.

### Prepare the Python environment
The easiest way to get the Python environment prepared is to use the setup scripts from
[camilladsp-setupscripts](https://github.com/HEnquist/camilladsp-setupscripts).

If doing a manual installation, there are many ways of installing Python and setting up environments.
Please see the [documentation for pycamilladsp](https://henquist.github.io/pycamilladsp/install/#installing)
for more information.

### Optional dependencies
The dependencies `matplotlib` and `numpy` are defined as optional,
and the pip command shown above will not install them if they are not already available.
To tell pip to install these dependencies, run:
```sh
pip install "camilladsp-plot[plot]@git+https://github.com/HEnquist/pycamilladsp-plot.git@v2.0.0"
```
The `[plot]` option tells pip to install also the optional dependencies `numpy` and `matplotlib`.
There is also a `[numpy]` option that includes `numpy` but not `matplotlib`. 


## Plotting a configuration from the command line
This library provides the console command `plotcamillaconf`. Once the library is installed, together with the optional dependencies numpy and matplotlib, the command should be available in your terminal.
To use it type:
```sh
plotcamillaconf /path/to/some/config.yml
```

This will plot the frequency response of all the defined filters, and show a block diagram of the pipeline. 
As a first step, the configuration is validated to ensure it is valid. 
If errors are found, these will be listed and no plots generated. It also shows a list of warnings. 
The warnings show possible problems that don't prevent the config from being used. 

Example:
```
Unable to plot, config has errors:
mixers/mono/mapping/sources/channel  :  -1 is less than the minimum of 0
filters/lowpass_2k/parameters/filename  :  Unable to find coefficent file 'sometext.txt'
pipeline/1/names/1  :  Use of missing filter 'notch_120'
pipeline/2/names/1  :  Use of missing filter 'notch_120'
pipeline  :  Pipeline outputs 4 channels, playback device has 2
```
The first part, before the ":" is the path in the config to where the error was found. The second part is a description of the error.


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

## Validating a config
A config file can be validated against a set of rules that match the ones in camilladsp. 

This example loads and validates a config from a path supplied on the command line. This example is for a Linux machine that does not have Pulse installed.
Therefore, the list of supported device types is updated to include only those supported on this system.
It then gets the error and warning lists, and the processed config. 
```python
import sys
from camilladsp_plot.validate_config import CamillaValidator
file_validator = CamillaValidator()
file_validator.set_supported_playback_types(["Alsa", "File", "Stdout"])
file_validator.set_supported_capture_types(["Alsa", "File", "Stdin"])
file_validator.validate_file(sys.argv[1])
errors = file_validator.get_errors()
warnings = file_validator.get_warnings()
config_with_defaults = file_validator.get_processed_config()
```

CamillaValidator also has `validate_yamlstring` which is used for a config supplied as a yaml string. There is also `validate_config` for configs that have already been parsed into a python object. 

# TODO
- pipeline view: leave out bypassed blocks
- pipeline view: indicate muted channels in mixers


