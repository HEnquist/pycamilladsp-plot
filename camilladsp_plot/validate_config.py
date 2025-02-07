import os
import sys
import json
import yaml
from copy import deepcopy
from importlib import resources

from jsonschema import Draft7Validator, validators

from camilladsp_plot.audiofileread import read_wav_header, read_text_coeffs

# Overall
with resources.files("camilladsp_plot").joinpath("schemas/sections.json").open('r') as f:
    section_schema = json.load(f)

# Devices
with resources.files("camilladsp_plot").joinpath("schemas/devices.json").open('r') as f:
    devices_schema = json.load(f)
with resources.files("camilladsp_plot").joinpath("schemas/playback.json").open('r') as f:
    playback_schemas = json.load(f)
with resources.files("camilladsp_plot").joinpath("schemas/capture.json").open('r') as f:
    capture_schemas = json.load(f)
with resources.files("camilladsp_plot").joinpath("schemas/resampler.json").open('r') as f:
    resampler_schemas = json.load(f)
with resources.files("camilladsp_plot").joinpath("schemas/signalgen.json").open('r') as f:
    signal_schemas = json.load(f)

# Filters
with resources.files("camilladsp_plot").joinpath("schemas/filter.json").open('r') as f:
    filter_schema = json.load(f)
with resources.files("camilladsp_plot").joinpath("schemas/biquads.json").open('r') as f:
    biquad_schemas = json.load(f)
with resources.files("camilladsp_plot").joinpath("schemas/biquadcombo.json").open('r') as f:
    biquadcombo_schemas = json.load(f)
with resources.files("camilladsp_plot").joinpath("schemas/conv.json").open('r') as f:
    conv_schemas = json.load(f)
with resources.files("camilladsp_plot").joinpath("schemas/dither.json").open('r') as f:
    dither_schemas = json.load(f)
with resources.files("camilladsp_plot").joinpath("schemas/basicfilters.json").open('r') as f:
    basics_schemas = json.load(f)

# Pipeline
with resources.files("camilladsp_plot").joinpath("schemas/pipeline.json").open('r') as f:
    pipeline_schemas = json.load(f)

# Mixer
with resources.files("camilladsp_plot").joinpath("schemas/mixer.json").open('r') as f:
    mixer_schema = json.load(f)

# Procesors
with resources.files("camilladsp_plot").joinpath("schemas/processor.json").open('r') as f:
    processor_schema = json.load(f)
with resources.files("camilladsp_plot").joinpath("schemas/compressor.json").open('r') as f:
    compressor_schema = json.load(f)
with resources.files("camilladsp_plot").joinpath("schemas/noisegate.json").open('r') as f:
    noisegate_schema = json.load(f)
with resources.files("camilladsp_plot").joinpath("schemas/race.json").open('r') as f:
    race_schema = json.load(f)
with resources.files("camilladsp_plot").joinpath("schemas/devices.json").open('r') as f:
    devices_schema = json.load(f)

# https://python-jsonschema.readthedocs.io/en/latest/faq/#why-doesn-t-my-schema-that-has-a-default-property-actually-set-the-default-on-my-instance

def extend_with_default(validator_class):
    validate_properties = validator_class.VALIDATORS["properties"]

    def set_defaults(validator, properties, instance, schema):
        for property, subschema in properties.items():
            if "default" in subschema and isinstance(instance, dict):
                instance.setdefault(property, subschema["default"])

        for error in validate_properties(
            validator,
            properties,
            instance,
            schema,
        ):
            yield error

    return validators.extend(
        validator_class,
        {"properties": set_defaults},
    )


class CamillaValidator:

    def __init__(self):
        self.config = None
        self.overrides = None
        self.validator = extend_with_default(Draft7Validator)

        self.capture_schemas = deepcopy(capture_schemas)
        self.playback_schemas = deepcopy(playback_schemas)

        self.errorlist = []
        self.warninglist = []

    def set_supported_capture_types(self, types):
        backup = self.capture_schemas_backup["capture"]["properties"]["type"]["enum"]
        common = list(set(backup).intersection(types))
        if len(common) == 0:
            raise ValueError("List of supported capture device types cannot be empty.")
        self.capture_schemas["capture"]["properties"]["type"]["enum"] = common

    def set_supported_playback_types(self, types):
        backup = self.playback_schemas_backup["playback"]["properties"]["type"]["enum"]
        common = list(set(backup).intersection(types))
        if len(common) == 0:
            raise ValueError("List of supported playback device types cannot be empty.")
        self.playback_schemas["playback"]["properties"]["type"]["enum"] = common

    def validate(self, config, schema, path=[]):
        ok = True
        for e in self.validator(schema).iter_errors(config):
            self.errorlist.append((path + list(e.path), e.message))
            ok = False
        return ok

    # return the override for a value if given, else just return the value
    def _override_value(self, value, parameter):
        if self.overrides is not None and self.overrides.get(parameter) is not None:
            if (
                parameter == "samplerate"
                and self.config["devices"].get("resampler") is not None
            ):
                # The config has a resampler, overriding samplerate changes only capture_samplerate.
                return value
            return self.overrides.get(parameter)
        return value

    def replace_tokens_in_string(self, string):
        srate = self.config["devices"]["samplerate"]
        srate = self._override_value(srate, "samplerate")
        channels = self.config["devices"]["capture"].get("channels")
        channels = self._override_value(channels, "channels")
        string = string.replace("$samplerate$", str(srate))
        string = string.replace("$channels$", str(channels))
        return string

    # Replace the $samplerate$ and $channels$ tokens with the corresponding values
    def replace_tokens(self):
        config = deepcopy(self.config)
        if config.get("filters") is not None:
            for _filt, fconf in config["filters"].items():
                if fconf["type"] == "Conv":
                    if "parameters" in fconf:
                        if "filename" in fconf["parameters"]:
                            fconf["parameters"]["filename"] = (
                                self.replace_tokens_in_string(
                                    fconf["parameters"]["filename"]
                                )
                            )

        if config.get("mixers") is not None:
            for step in config["pipeline"]:
                if step["type"] == "Mixer":
                    step["name"] = self.replace_tokens_in_string(step["name"])
                elif step["type"] == "Filter":
                    for _i, name in enumerate(step["names"]):
                        name = self.replace_tokens_in_string(name)
        return config

    def make_paths_absolute(self, config):
        if config.get("filters") is not None:
            for _name, filt in config["filters"].items():
                if filt["type"] == "Conv" and filt["parameters"]["type"] in [
                    "Raw",
                    "Wav",
                ]:
                    filt["parameters"]["filename"] = (
                        self.check_and_replace_relative_path(
                            filt["parameters"]["filename"]
                        )
                    )

    def check_and_replace_relative_path(self, path_str):
        if self.filename is None:
            return path_str
        config_dir = os.path.dirname(os.path.abspath(self.filename))
        if not os.path.isabs(path_str):
            in_config_dir = os.path.join(config_dir, path_str)
            if os.path.exists(in_config_dir):
                # File found relative to config file
                return in_config_dir
        # No change, just return it again
        return path_str

    # Validate a file read from disk
    def validate_file(self, file, overrides=None):
        self.errorlist = []
        self.warninglist = []
        self.filename = file
        self.overrides = overrides
        with open(file) as f:
            try:
                self.config = yaml.safe_load(f)
            except yaml.YAMLError as e:
                msg = f"YAML syntax error on line {e.problem_mark.line+1}"
                self.errorlist.append(([], msg))
                self.config = None
                return
            except Exception as e:
                msg = f"Error reading file, error: {e}"
                self.errorlist.append(([], msg))
                self.config = None
                return
        self._validate_config()

    # Validate a config supplied as a yaml string
    def validate_yamlstring(self, config, overrides=None):
        self.errorlist = []
        self.warninglist = []
        self.filename = None
        self.overrides = overrides
        try:
            self.config = yaml.safe_load(config)
        except yaml.YAMLError as e:
            msg = f"YAML syntax error on line {e.problem_mark.line+1}"
            self.errorlist.append(([], msg))
            self.config = None
            return
        except Exception as e:
            msg = f"Error reading config, error: {e}"
            self.errorlist.append(([], msg))
            self.config = None
            return
        self._validate_config()

    # Validate a config already parsed into a python object
    def validate_config(self, config, overrides=None):
        self.errorlist = []
        self.warninglist = []
        self.filename = None
        self.config = config
        self.overrides = overrides
        self._validate_config()

    def _validate_config(self):
        self._check_overrides()
        self.validate_with_schemas()
        if len(self.errorlist) == 0:
            self.validate_devices()
            self.validate_mixers()
            self.validate_filters()
            self.validate_processors()
            self.validate_pipeline()

    # Check that the supplied overrides are valid, null them if not
    def _check_overrides(self):
        if self.overrides is None:
            return
        if not isinstance(self.overrides, dict):
            self.overrides = None
            return

    # Return the validated config.
    # All missing values have been filled by defaults.
    # Tokens are preserved.
    def get_config(self):
        return self.config

    # Return the validated and processed config.
    # All missing values have been filled by defaults.
    # Tokens are replaced by their values.
    def get_processed_config(self):
        if self.config:
            config = self.replace_tokens()
            if self.filename is not None:
                self.make_paths_absolute(config)
            return config, self.overrides
        return None

    # Get the list of errors
    def get_errors(self):
        return self.errorlist

    # Get the list of warnings
    def get_warnings(self):
        return self.warninglist

    def validate_with_schemas(self):
        # Overall structure
        self.validate(self.config, section_schema)

        # Devices section
        self.validate(self.config["devices"], devices_schema, path=["devices"])

        # Playback device
        playback_schema = self.playback_schemas["playback"]
        ok = self.validate(
            self.config["devices"]["playback"],
            playback_schema,
            path=["devices", "playback"],
        )
        if ok:
            playback_type = self.config["devices"]["playback"]["type"]
            playback_schema = self.playback_schemas[playback_type]
            self.validate(
                self.config["devices"]["playback"],
                playback_schema,
                path=["devices", "playback"],
            )

        # Capture device
        capture_schema = self.capture_schemas["capture"]
        ok = self.validate(
            self.config["devices"]["capture"],
            capture_schema,
            path=["devices", "capture"],
        )
        if ok:
            capture_type = self.config["devices"]["capture"]["type"]
            capture_schema = self.capture_schemas[capture_type]
            self.validate(
                self.config["devices"]["capture"],
                capture_schema,
                path=["devices", "capture"],
            )
            if capture_type == "SignalGenerator":
                signal_schema = signal_schemas["signal"]
                ok = self.validate(
                    self.config["devices"]["capture"]["signal"],
                    signal_schema,
                    path=["devices", "capture", "signal"],
                )
                if ok:
                    signal_type = self.config["devices"]["capture"]["signal"]["type"]
                    signal_schema = signal_schemas[signal_type]
                    self.validate(
                        self.config["devices"]["capture"]["signal"],
                        signal_schema,
                        path=["devices", "capture", "signal"],
                    )

        # Resampler
        if self.config["devices"].get("resampler") is not None:
            self.validate(
                self.config["devices"]["resampler"],
                resampler_schemas["resampler"],
                path=["devices", "resampler"],
            )
            resamp_type = self.config["devices"]["resampler"]["type"]
            if resamp_type in ["Synchronous", "AsyncPoly"]:
                resampler_schema = resampler_schemas[resamp_type]
            elif "profile" in self.config["devices"]["resampler"]:
                resampler_schema = resampler_schemas["AsyncSincProfile"]
            else:
                resampler_schema = resampler_schemas["AsyncSincFree"]
            self.validate(
                self.config["devices"]["resampler"],
                resampler_schema,
                path=["devices", "resampler"],
            )

        # Filters
        for name, filt in self.value_or_default(("filters",)).items():
            ok = self.validate(filt, filter_schema, path=["filters", name])
            if ok:
                filt_type = filt["type"]
                if filt_type == "Biquad":
                    schema = biquad_schemas["Biquad"]
                    ok = self.validate(
                        filt["parameters"], schema, path=["filters", name, "parameters"]
                    )
                    if ok:
                        filt_subtype = filt["parameters"]["type"]
                        schema = biquad_schemas[filt_subtype]
                        self.validate(
                            filt["parameters"],
                            schema,
                            path=["filters", name, "parameters"],
                        )
                elif filt_type == "BiquadCombo":
                    schema = biquadcombo_schemas["BiquadCombo"]
                    ok = self.validate(
                        filt["parameters"], schema, path=["filters", name, "parameters"]
                    )
                    if ok:
                        filt_subtype = filt["parameters"]["type"]
                        schema = biquadcombo_schemas[filt_subtype]
                        self.validate(
                            filt["parameters"],
                            schema,
                            path=["filters", name, "parameters"],
                        )
                elif filt_type == "Conv":
                    schema = conv_schemas["Conv"]
                    ok = self.validate(
                        filt["parameters"], schema, path=["filters", name, "parameters"]
                    )
                    if ok:
                        filt_subtype = filt["parameters"]["type"]
                        schema = conv_schemas[filt_subtype]
                        self.validate(
                            filt["parameters"],
                            schema,
                            path=["filters", name, "parameters"],
                        )
                elif filt_type == "Dither":
                    schema = dither_schemas["Dither"]
                    ok = self.validate(
                        filt["parameters"], schema, path=["filters", name, "parameters"]
                    )
                    if ok:
                        filt_subtype = filt["parameters"]["type"]
                        if filt_subtype in dither_schemas.keys():
                            schema = dither_schemas[filt_subtype]
                            self.validate(
                                filt["parameters"],
                                schema,
                                path=["filters", name, "parameters"],
                            )
                elif filt_type in basics_schemas.keys():
                    schema = basics_schemas[filt_type]
                    self.validate(
                        filt["parameters"], schema, path=["filters", name, "parameters"]
                    )

        # Mixers
        for name, mix in self.value_or_default(("mixers",)).items():
            self.validate(mix, mixer_schema, path=["mixers", name])

        # Processors
        for name, prc in self.value_or_default(("processors",)).items():
            ok = self.validate(prc, processor_schema, path=["processors", name])
            if ok:
                prc_type = prc["type"]
                if prc_type == "Compressor":
                    schema = compressor_schema
                    ok = self.validate(
                        prc["parameters"], schema, path=["processors", name, "parameters"]
                    )
                elif prc_type == "NoiseGate":
                    schema = noisegate_schema
                    ok = self.validate(
                        prc["parameters"], schema, path=["processors", name, "parameters"]
                    )
                elif prc_type == "RACE":
                    schema = race_schema
                    ok = self.validate(
                        prc["parameters"], schema, path=["processors", name, "parameters"]
                    )

        # Pipeline
        for idx, step in enumerate(self.value_or_default(("pipeline",))):
            ok = self.validate(
                step, pipeline_schemas["PipelineStep"], path=["pipeline", idx]
            )
            if ok:
                step_type = step["type"]
                schema = pipeline_schemas[step_type]
                self.validate(step, schema, path=["pipeline", idx])

    # Validate the pipeline
    def validate_pipeline(self):
        num_channels = self.config["devices"]["capture"].get("channels")
        num_channels = self._override_value(num_channels, "channels")
        for idx, step in enumerate(self.value_or_default(("pipeline",))):
            if step["type"] == "Mixer":
                mixname_with_tokens = step["name"]
                mixname = self.replace_tokens_in_string(mixname_with_tokens)
                if mixname not in self.config["mixers"].keys():
                    msg = f"Use of missing mixer '{mixname}'"
                    path = ["pipeline", idx, "name"]
                    self.errorlist.append((path, msg))
                else:
                    chan_in = self.config["mixers"][mixname]["channels"]["in"]
                    if chan_in != num_channels:
                        msg = f"Mixer '{mixname}' has wrong number of input channels. Expected {num_channels}, found {chan_in}"
                        path = ["pipeline", idx]
                        self.errorlist.append((path, msg))
                    num_channels = self.config["mixers"][mixname]["channels"]["out"]

            if step["type"] == "Filter":
                if step["channels"] is not None:
                    for chan in step["channels"]:
                        if chan >= num_channels:
                            msg = f"Use of non existing channel {chan}"
                            path = ["pipeline", idx, "channels"]
                            self.errorlist.append((path, msg))
                for subidx, filtname_with_tokens in enumerate(step["names"]):
                    filtname = self.replace_tokens_in_string(filtname_with_tokens)
                    if filtname not in self.config["filters"].keys():
                        msg = f"Use of missing filter '{filtname}'"
                        path = ["pipeline", idx, "names", subidx]
                        self.errorlist.append((path, msg))

            if step["type"] == "Processor":
                prcname_with_tokens = step["name"]
                prcname = self.replace_tokens_in_string(prcname_with_tokens)
                if prcname not in self.config["processors"].keys():
                    msg = f"Use of missing processor '{prcname}'"
                    path = ["pipeline", idx, "name"]
                    self.errorlist.append((path, msg))
                else:
                    channels = self.config["processors"][prcname]["parameters"]["channels"]
                    if channels != num_channels:
                        msg = f"Processor '{prcname}' has wrong number of channels. Expected {num_channels}, found {channels}"
                        path = ["pipeline", idx]
                        self.errorlist.append((path, msg))

        num_channels_out = self.config["devices"]["playback"]["channels"]
        if num_channels != num_channels_out:
            msg = f"Pipeline outputs {num_channels} channels, playback device has {num_channels_out}"
            path = ["pipeline"]
            self.errorlist.append((path, msg))

    def validate_mixers(self):
        for mixname, mixer_config in self.value_or_default(("mixers",)).items():
            chan_in = mixer_config["channels"]["in"]
            chan_out = mixer_config["channels"]["out"]
            for idx, mapping in enumerate(mixer_config["mapping"]):
                if mapping["dest"] >= chan_out:
                    msg = f"Invalid destination channel {mapping['dest']}, max is {chan_out-1}"
                    path = ["mixers", mixname, "mapping", idx, "dest"]
                    self.errorlist.append((path, msg))
                for subidx, source in enumerate(mapping["sources"]):
                    if source["channel"] >= chan_in:
                        msg = f"Invalid source channel {source['channel']}, max is {chan_in-1}"
                        path = ["mixers", mixname, "mapping", idx, "sources", subidx]
                        self.errorlist.append((path, msg))

    def validate_filters(self):
        samplerate = self.config["devices"]["samplerate"]
        samplerate = self._override_value(samplerate, "samplerate")
        maxfreq = samplerate / 2.0

        for filter_name, filter_conf in self.value_or_default(("filters",)).items():
            # Check that frequencies are below Nyquist
            if filter_conf["type"] in ["Biquad", "BiquadCombo"]:
                for freq_prop in [
                    "freq",
                    "freq_act",
                    "freq_target",
                    "fls",
                    "fhs",
                    "fp1",
                    "fp2",
                    "fp3",
                    "freq_p",
                    "freq_z",
                    "freq_min",
                    "freq_max",
                ]:
                    if freq_prop in filter_conf["parameters"].keys():
                        if filter_conf["parameters"][freq_prop] >= maxfreq:
                            msg = "Frequency must be < samplerate/2"
                            path = ["filters", filter_name, "parameters", freq_prop]
                            self.errorlist.append((path, msg))
            # Check that free biquads are stable
            if (
                filter_conf["type"] == "Biquad"
                and filter_conf["parameters"]["type"] == "Free"
            ):
                a1 = filter_conf["parameters"]["a1"]
                a2 = filter_conf["parameters"]["a2"]
                stable = abs(a2) < 1.0 and abs(a1) < (a2 + 1.0)
                if not stable:
                    msg = "Filter is unstable"
                    path = ["filters", filter_name, "parameters"]
                    self.errorlist.append((path, msg))
            # Check that Biquads have at only one of q and bandwidth
            if filter_conf["type"] == "Biquad" and filter_conf["parameters"][
                "type"
            ] in ["Bandpass", "Notch", "Allpass", "Peaking"]:
                has_q = "q" in filter_conf["parameters"]
                has_bw = "bandwidth" in filter_conf["parameters"]
                if not has_q and not has_bw:
                    msg = "Missing 'bandwidth' or 'q', one must be given"
                    path = ["filters", filter_name, "parameters"]
                    self.errorlist.append((path, msg))
                if has_q and has_bw:
                    msg = "Both 'bandwidth' and 'q' given, only one is allowed"
                    path = ["filters", filter_name, "parameters"]
                    self.errorlist.append((path, msg))
            # Check that GraphicEqualizer min frequency is smaller than max frequency
            if (
                filter_conf["type"] == "BiquadCombo"
                and filter_conf["parameters"]["type"] == "GraphicEqualizer"
            ):
                f_max = self.value_or_default(
                    ("parameters", "freq_max"), config=filter_conf
                )
                f_min = self.value_or_default(
                    ("parameters", "freq_min"), config=filter_conf
                )
                if f_max <= f_min:
                    msg = "Invalid range, 'freq_max' must be larger than 'freq_min'"
                    path = ["filters", filter_name, "parameters", "freq_max"]
                    self.errorlist.append((path, msg))
            # Check that Biquads have at only one of q and slope
            if filter_conf["type"] == "Biquad" and filter_conf["parameters"][
                "type"
            ] in ["Highshelf", "Lowshelf"]:
                has_q = "q" in filter_conf["parameters"]
                has_slope = "slope" in filter_conf["parameters"]
                if not has_q and not has_slope:
                    msg = "Missing 'slope' or 'q', one must be given"
                    path = ["filters", filter_name, "parameters"]
                    self.errorlist.append((path, msg))
                if has_q and has_slope:
                    msg = "Both 'slope' and 'q' given, only one is allowed"
                    path = ["filters", filter_name, "parameters"]
                    self.errorlist.append((path, msg))
            # Check that coefficients files are available
            if filter_conf["type"] == "Conv":
                if filter_conf["parameters"]["type"] in ["Raw", "Wav"]:
                    fname_with_tokens = filter_conf["parameters"]["filename"]
                    fname_rel = self.replace_tokens_in_string(fname_with_tokens)
                    fname = self.check_and_replace_relative_path(fname_rel)
                    if not os.path.exists(fname):
                        msg = f"Unable to find coefficent file '{fname}'"
                        path = ["filters", filter_name, "parameters", "filename"]
                        self.errorlist.append((path, msg))
                        continue
                    if filter_conf["parameters"]["type"] == "Wav":
                        wavparams = read_wav_header(fname)
                        if wavparams is None:
                            msg = f"Invalid or unsupported wav file '{fname}'"
                            path = ["filters", filter_name, "parameters", "filename"]
                            self.errorlist.append((path, msg))
                        elif (
                            self.value_or_default(
                                ("parameters", "channel"), config=filter_conf
                            )
                            >= wavparams["channels"]
                        ):
                            msg = f"Can't read channel {self.value_or_default(('parameters', 'channel'), config=filter_conf)} of file '{fname}' which has channels 0..{wavparams['channels']-1}"
                            path = ["filters", filter_name, "parameters", "filename"]
                            self.errorlist.append((path, msg))
                        elif wavparams["samplerate"] != samplerate:
                            msg = f"Sample rate mismatch, file '{fname}': {wavparams['samplerate']}, dsp: {samplerate}"
                            path = ["filters", filter_name, "parameters", "filename"]
                            self.warninglist.append((path, msg))
                    elif filter_conf["parameters"]["type"] == "Raw":
                        if filter_conf["parameters"]["format"] == "TEXT":
                            try:
                                values = read_text_coeffs(
                                    fname,
                                    self.value_or_default(
                                        ("parameters", "skip_bytes_lines"),
                                        config=filter_conf,
                                    ),
                                    self.value_or_default(
                                        ("parameters", "read_bytes_lines"),
                                        config=filter_conf,
                                    ),
                                )
                                if len(values) == 0:
                                    msg = f"File '{fname}' contains no values"
                                    path = [
                                        "filters",
                                        filter_name,
                                        "parameters",
                                        "filename",
                                    ]
                                    self.errorlist.append((path, msg))
                            except ValueError as e:
                                msg = (
                                    f"File '{fname}' contains invalid numbers, {str(e)}"
                                )
                                path = [
                                    "filters",
                                    filter_name,
                                    "parameters",
                                    "filename",
                                ]
                                self.errorlist.append((path, msg))
                            except Exception as e:
                                msg = f"Cant open file '{fname}', {str(e)}"
                                path = [
                                    "filters",
                                    filter_name,
                                    "parameters",
                                    "filename",
                                ]
                                self.errorlist.append((path, msg))
                        else:
                            try:
                                with open(fname, "rb") as f:
                                    f.seek(0, 2)
                                    coeff_len = f.tell()
                                if coeff_len <= self.value_or_default(
                                    ("parameters", "skip_bytes_lines"),
                                    config=filter_conf,
                                ):
                                    msg = f"File '{fname}' contains no values"
                                    path = [
                                        "filters",
                                        filter_name,
                                        "parameters",
                                        "filename",
                                    ]
                                    self.errorlist.append((path, msg))
                            except Exception as e:
                                msg = f"Cant open file '{fname}', {str(e)}"
                                path = [
                                    "filters",
                                    filter_name,
                                    "parameters",
                                    "filename",
                                ]
                                self.errorlist.append((path, msg))

    def validate_devices(self):
        if self.config["devices"]["playback"]["type"] == "Alsa":
            # With Alsa playback we can allow a limit of up to 4 chunks
            target_level_limit = 4 * self.config["devices"]["chunksize"]
        else:
            target_level_limit = 2 * self.config["devices"]["chunksize"]
        if self.value_or_default(("devices", "target_level")) > target_level_limit:
            self.errorlist.append(
                (
                    ["devices", "target_level"],
                    f"target_level cannot be larger than {target_level_limit}",
                )
            )

        # Specific checks for Wasapi
        if self.config["devices"]["capture"]["type"] == "Wasapi":
            if self.value_or_default(
                ("devices", "capture", "loopback")
            ) and self.value_or_default(("devices", "capture", "exclusive")):
                self.errorlist.append(
                    (
                        ["devices", "capture", "exclusive"],
                        "exclusive mode cannot be combined with loopback capture",
                    )
                )
            if (
                not self.value_or_default(("devices", "capture", "exclusive"))
                and self.config["devices"]["capture"]["format"] != "FLOAT32LE"
            ):
                self.errorlist.append(
                    (
                        ["devices", "capture", "format"],
                        "in shared mode the format must be FLOAT32LE",
                    )
                )
        if self.config["devices"]["playback"]["type"] == "Wasapi":
            if (
                not self.value_or_default(("devices", "capture", "exclusive"))
                and self.config["devices"]["playback"]["format"] != "FLOAT32LE"
            ):
                self.errorlist.append(
                    (
                        ["devices", "playback", "format"],
                        "in shared mode the format must be FLOAT32LE",
                    )
                )

        # Checks for WavFile capture device
        if self.config["devices"]["capture"]["type"] == "WavFile":
            fname = self.config["devices"]["capture"]["filename"]
            wavparams = read_wav_header(fname)
            if wavparams is None:
                msg = f"Invalid or unsupported wav file '{fname}'"
                path = ["devices", "capture", "filename"]
                self.errorlist.append((path, msg))
            else:
                if self.overrides is None:
                    self.overrides = {}
                self.overrides["samplerate"] = wavparams["samplerate"]
                self.overrides["channels"] = wavparams["channels"]

    def validate_processors(self):
        for proc_name, proc_conf in self.value_or_default(("processors",)).items():
            num_channels = proc_conf["parameters"]["channels"]
            if proc_conf["type"] in ["Compressor", "NoiseGate"]:
                monitor_channels = proc_conf["parameters"]["monitor_channels"]
                if monitor_channels is not None and any(ch >= num_channels for ch in monitor_channels):
                    bad_channels = ", ".join(str(ch) for ch in monitor_channels if ch >= num_channels)
                    msg = f"Processor '{proc_name}' monitors non-existing channel(s) {bad_channels}. Max is {num_channels-1}"
                    path = ["processors", proc_name, "parameters", "monitor_channels"]
                    self.errorlist.append((path, msg))
                process_channels = proc_conf["parameters"]["process_channels"]
                if process_channels is not None and any(ch >= num_channels for ch in process_channels):
                    bad_channels = ", ".join(str(ch) for ch in process_channels if ch >= num_channels)
                    msg = f"Processor '{proc_name}' processes non-existing channel(s) {bad_channels}. Max is {num_channels-1}"
                    path = ["processors", proc_name, "parameters", "process_channels"]
                    self.errorlist.append((path, msg))
            elif proc_conf["type"] == "RACE":
                channel_a = proc_conf["parameters"]["channel_a"]
                if channel_a >= num_channels:
                    msg = f"Invalid value for channel_a, max is {num_channels-1}"
                    path = ["processors", proc_name, "parameters", "channel_a"]
                    self.errorlist.append((path, msg))
                channel_b = proc_conf["parameters"]["channel_b"]
                if channel_b >= num_channels:
                    msg = f"Invalid value for channel_b, max is {num_channels-1}"
                    path = ["processors", proc_name, "parameters", "channel_b"]
                    self.errorlist.append((path, msg))
                if channel_b == channel_a:
                    msg = f"Values for channel_a and channel_b must be different"
                    path = ["processors", proc_name, "parameters", "channel_b"]
                    self.errorlist.append((path, msg))

    def value_or_default(self, path, config=None):
        if config:
            val = config
        else:
            val = self.config
        for p in path:
            val = val.get(p, {})
        if val is None:
            return self.lookup_default(path)
        return val

    def lookup_default(self, path):
        if path == ("devices", "target_level"):
            return self.config["devices"]["chunksize"]
        return DEFAULT_VALUES.get(path)


DEFAULT_VALUES = {
    ("filters",): {},
    ("mixers",): {},
    ("processors",): {},
    ("pipeline",): [],
    ("devices", "capture", "loopback"): False,
    ("devices", "capture", "exclusive"): False,
    ("parameters", "freq_min"): 20.0,
    ("parameters", "freq_max"): 20000.0,
    ("parameters", "format"): "TEXT",
    ("parameters", "skip_bytes_lines"): 0,
    ("parameters", "read_bytes_lines"): 0,
    ("parameters", "channel"): 0,
}

if __name__ == "__main__":
    file_validator = CamillaValidator()
    file_validator.validate_file(sys.argv[1])
    errors = file_validator.get_errors()
    warnings = file_validator.get_warnings()
    print("\nErrors:")
    for e in errors:
        print("/".join([str(p) for p in e[0]]), " : ", e[1])
    print("\nWarnings:")
    for w in warnings:
        print("/".join([str(p) for p in w[0]]), " : ", w[1])
