import json                                                             
import yaml                                                             

from jsonschema import Draft7Validator, validators, ValidationError
import os
import sys
from .audiofileread import read_wav_header, read_text_coeffs

# https://python-jsonschema.readthedocs.io/en/latest/faq/#why-doesn-t-my-schema-that-has-a-default-property-actually-set-the-default-on-my-instance
def extend_with_default(validator_class):
    validate_properties = validator_class.VALIDATORS["properties"]

    def set_defaults(validator, properties, instance, schema):
        for property, subschema in properties.items():
            if "default" in subschema:
                instance.setdefault(property, subschema["default"])

        for error in validate_properties(
            validator, properties, instance, schema,
        ):
            yield error

    return validators.extend(
        validator_class, {"properties" : set_defaults},
    )

class CamillaValidator():

    def __init__(self):
        self.config = None
        self.validator = extend_with_default(Draft7Validator)
        # Overall
        with open(self.get_full_path("schemas/sections.json")) as f:
            self.section_schema = json.load(f)

        # Devices
        with open(self.get_full_path("schemas/devices.json")) as f:
            self.devices_schema = json.load(f)
        with open(self.get_full_path("schemas/playback.json")) as f:
            self.playback_schemas = json.load(f)
        with open(self.get_full_path("schemas/capture.json")) as f:
            self.capture_schemas = json.load(f)

        # Filters
        with open(self.get_full_path("schemas/filter.json")) as f:
            self.filter_schema = json.load(f)
        with open(self.get_full_path("schemas/biquads.json")) as f:
            self.biquad_schemas = json.load(f)
        with open(self.get_full_path("schemas/biquadcombo.json")) as f:
            self.biquadcombo_schemas = json.load(f)
        with open(self.get_full_path("schemas/conv.json")) as f:
            self.conv_schemas = json.load(f)
        with open(self.get_full_path("schemas/basicfilters.json")) as f:
            self.basics_schemas = json.load(f)

        # Pipeline
        with open(self.get_full_path("schemas/pipeline.json")) as f:
            self.pipeline_schemas = json.load(f)

        # Mixer
        with open(self.get_full_path("schemas/mixer.json")) as f:
            self.mixer_schema = json.load(f)

        self.errorlist = []
        self.warninglist = []


    def validate(self, config, schema, path=[]):
        try:
            self.validator(schema).validate(config)
        except ValidationError as e:
            self.errorlist.append((path + list(e.path), e.message))

    # DefaultValidatingDraft7Validator(schema).validate(obj)
    def get_full_path(self, file):
        return os.path.join(os.path.dirname(__file__), file)

    # Replace the $samplerate$ and $channels$ tokens with the corresponding values
    def replace_tokens(self):
        srate = self.config['devices']['samplerate']
        channels = self.config['devices']['capture']['channels']

        for _filt, fconf in self.config['filters'].items():
            if fconf['type'] == 'Conv':
                if 'parameters' in fconf:
                    if "filename" in fconf['parameters']:
                        fconf['parameters']["filename"] = fconf['parameters']["filename"].replace("$samplerate$", str(srate))
                        fconf['parameters']["filename"] = fconf['parameters']["filename"].replace("$channels$", str(channels))

        for step in self.config['pipeline']:
            if step['type'] == 'Mixer':
                step['name'] = step['name'].replace("$samplerate$", str(srate))
                step['name'] = step['name'].replace("$channels$", str(channels))
            elif step['type'] == 'Filter':
                for _i, name in enumerate(step['names']):
                    name = name.replace("$samplerate$", str(srate))
                    name = name.replace("$channels$", str(channels))

    def make_paths_absolute(self):
        config_dir = os.path.dirname(os.path.abspath(self.filename))
        for _name, filt in self.config["filters"].items():
            if filt["type"] == "Conv" and filt["parameters"]["type"] == "File":
                filt["parameters"]["filename"] = self.check_and_replace_relative_path(filt["parameters"]["filename"], config_dir)

    def check_and_replace_relative_path(self, path_str, config_dir):
        if not os.path.isabs(path_str):
            in_config_dir = os.path.join(config_dir, path_str)
            if os.path.exists(in_config_dir):
                # File found relative to config file
                return in_config_dir
        # No change, just return it again
        return path_str

    # Validate a file read from disk
    def validate_file(self, file):
        self.errorlist = []
        self.warninglist = []
        self.filename = file
        with open(file) as f:
            try:
                self.config = yaml.safe_load(f)
            except Exception as e:
                self.errorlist.append(([], str(e)))
                return
        self._validate_config()

    # Validate a config supplied as a yaml string
    def validate_yamlstring(self, config):
        self.errorlist = []
        self.warninglist = []
        self.filename = None
        try:
            self.config = yaml.safe_load(config)
        except Exception as e:
            self.errorlist.append(([], str(e)))
            return
        self._validate_config()

    # Validate a config already parsed into a python object
    def validate_config(self, config):
        self.errorlist = []
        self.warninglist = []
        self.config = config
        self._validate_config()

    def _validate_config(self):
        self.validate_with_schemas()
        if self.filename is not None:
            self.make_paths_absolute()
        self.replace_tokens()

        self.validate_devices()
        self.validate_mixers()
        self.validate_filters()
        self.validate_pipeline()

    # Return the processed config. All missing values have been filled by defaults 
    def get_config(self):
        return self.config

    # Get the list of errors
    def get_errors(self):
        return self.errorlist
    
    # Get the list of warnings
    def get_warnings(self):
        return self.warninglist

    def validate_with_schemas(self):
        # Overall structure
        self.validate(self.config, self.section_schema)
        #print(yaml.dump(conf, sort_keys=True))

        # Devices section
        self.validate(self.config["devices"], self.devices_schema, path=["devices"])

        # Playback device
        playback_type = self.config["devices"]["playback"]["type"]
        playback_schema = self.playback_schemas[playback_type]
        self.validate(self.config["devices"]["playback"], playback_schema, path=["devices", "playback"])

        # Capture device
        capture_type = self.config["devices"]["capture"]["type"]
        capture_schema = self.capture_schemas[capture_type]
        self.validate(self.config["devices"]["capture"], capture_schema, path=["devices", "capture"])

        # Filters
        if "filters" in self.config: 
            for name, filt in self.config["filters"].items():
                print(f"Validating filter {name}")
                self.validate(filt, self.filter_schema, path=["filters", name])
                filt_type = filt["type"]
                filt_subtype = filt["parameters"]["type"]
                if filt_type == "Biquad":
                    schema = self.biquad_schemas["Biquad"]
                    self.validate(filt["parameters"], schema, path=["filters", name, "parameters"])
                    schema = self.biquad_schemas[filt_subtype]
                    self.validate(filt["parameters"], schema, path=["filters", name, "parameters"])
                elif filt_type == "BiquadCombo":
                    schema = self.biquadcombo_schemas["BiquadCombo"]
                    self.validate(filt["parameters"], schema, path=["filters", name, "parameters"])
                    schema = self.biquadcombo_schemas[filt_subtype]
                    self.validate(filt["parameters"], schema, path=["filters", name, "parameters"])
                elif filt_type == "Conv":
                    schema = self.conv_schemas["Conv"]
                    self.validate(filt["parameters"], schema, path=["filters", name, "parameters"])
                    schema = self.conv_schemas[filt_subtype]
                    self.validate(filt["parameters"], schema, path=["filters", name, "parameters"])
                elif filt_type in self.basics_schemas.keys():
                    schema = self.basics_schemas[filt_type]
                    self.validate(filt["parameters"], schema, path=["filters", name, "parameters"])

        # Mixers
        if "mixers" in self.config: 
            for name, mix in self.config["mixers"].items():
                print(f"Validating mixer {name}")
                self.validate(mix, self.mixer_schema, path=["mixers", name])

        # Pipeline
        if "pipeline" in self.config: 
            for idx, step in enumerate(self.config["pipeline"]):
                print(f"Validating pipeline step")
                self.validate(step, self.pipeline_schemas["PipelineStep"], path=["pipeline", idx])
                step_type = step["type"]
                schema = self.pipeline_schemas[step_type]
                self.validate(step, schema, path=["pipeline", idx])

    # Validate the pipeline
    def validate_pipeline(self):
        num_channels = self.config["devices"]["capture"]["channels"]
        for idx, step in enumerate(self.config["pipeline"]):
            if step["type"] == "Mixer":
                mixname = step["name"]
                if mixname not in self.config["mixers"].keys():
                    msg = f"Use of missing mixer '{mixname}'"
                    path = ["pipeline", idx]
                    self.errorlist.append((path, msg))
                else:
                    chan_in = self.config["mixers"][mixname]["channels"]["in"]
                    if chan_in != num_channels:
                        msg = f"Mixer '{mixname}' has wrong number of input channels. Expected {num_channels}, found {chan_in}"
                        path = ["pipeline", idx]
                        self.errorlist.append((path, msg))
                    num_channels = self.config["mixers"][mixname]["channels"]["out"]

            if step["type"] == "Filter":
                if step["channel"] >= num_channels:
                    msg = f"Use of non existing channel {step['channel']}"
                    path = ["pipeline", idx]
                    self.errorlist.append((path, msg))
                for subidx, filtname in enumerate(step["names"]):
                    if filtname not in self.config["filters"].keys():
                        msg = f"Use of missing filter '{filtname}'"
                        path = ["pipeline", idx, "names", subidx]
                        self.errorlist.append((path, msg))

        num_channels_out = self.config["devices"]["playback"]["channels"]
        if num_channels != num_channels_out:
            msg = f"Pipeline outputs {num_channels} channels, playback device has {num_channels_out}"
            path = ["pipeline"]
            self.errorlist.append((path, msg))


    def validate_mixers(self):
        for mixname, mixer_config in self.config["mixers"].items():
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
        maxfreq = self.config["devices"]["samplerate"] / 2.0
        for filter_name, filter_conf in self.config["filters"].items():
            # Check that frequencies are below Nyquist
            if filter_conf["type"] in ["Biquad", "BiquadCombo"]:
                for freq_prop in ["freq", "freq_act", "freq_target"]:
                    if freq_prop in filter_conf["parameters"].keys():
                        if filter_conf["parameters"][freq_prop] >= maxfreq:
                            msg = "Frequency must be < samplerate/2"
                            path = ["filters", filter_name, "parameters", freq_prop]
                            self.errorlist.append((path, msg))
            # Check that free biquads are stable
            if filter_conf["type"] == "Biquad" and  filter_conf["parameters"]["type"] == "Free":
                a1 = filter_conf["parameters"]["a1"]
                a2 = filter_conf["parameters"]["a2"]
                stable = abs(a2) < 1.0 and abs(a1) < (a2 + 1.0)
                if not stable:
                    msg = "Filter is unstable"
                    path = ["filters", filter_name, "parameters"]
                    self.errorlist.append((path, msg))
            # Check that coefficients files are available
            if filter_conf["type"] == "Conv":
                if filter_conf["parameters"]["type"] in ["Raw", "Wav"]:
                    fname = filter_conf["parameters"]["filename"]
                    if not os.path.exists(fname):
                        msg = f"Unable to find coefficent file '{fname}'"
                        path = ["filters", filter_name, "parameters", "filename"]
                        self.errorlist.append((path, msg))
                    if filter_conf["parameters"]["type"] == "Wav":
                        wavparams = read_wav_header(fname)
                        if wavparams is None:
                            msg = f"Invalid or unsupported wav file '{fname}'"
                            path = ["filters", filter_name, "parameters", "filename"]
                            self.errorlist.append((path, msg))
                        elif filter_conf["parameters"]["channel"] >= wavparams["channels"]:
                            msg = f"Can't read channel {filter_conf['parameters']['channel']} of file '{fname}' which has channels 0..{wavparams['channels']-1}"
                            path = ["filters", filter_name, "parameters", "filename"]
                            self.errorlist.append((path, msg))
                        elif wavparams["samplerate"] != self.config["devices"]["samplerate"]:
                            msg = f"Sample rate mismatch, file '{fname}': {wavparams['samplerate']}, dsp: {self.config['devices']['samplerate']}"
                            path = ["filters", filter_name, "parameters", "filename"]
                            self.warninglist.append((path, msg))
                    elif filter_conf["parameters"]["type"] == "Raw":
                        if filter_conf["parameters"]["format"] == "TEXT":
                            try:
                                values = read_text_coeffs(fname, filter_conf["parameters"]["skip_bytes_lines"], filter_conf["parameters"]["read_bytes_lines"])
                            except ValueError as e:
                                msg = f"File '{fname}' contains invalid numbers, {str(e)}"
                                path = ["filters", filter_name, "parameters", "filename"]
                                self.errorlist.append((path, msg))
                            if len(values)<1:
                                msg = f"File '{fname}' contains no values"
                                path = ["filters", filter_name, "parameters", "filename"]
                                self.errorlist.append((path, msg))
                        else:
                            with open(fname, 'rb') as f:
                                coeff_len = f.tell()
                            if coeff_len <= filter_conf["parameters"]["skip_bytes_lines"]:
                                msg = f"File '{fname}' contains no values"
                                path = ["filters", filter_name, "parameters", "filename"]
                                self.errorlist.append((path, msg))


    def validate_devices(self):
        if self.config["devices"]["target_level"] >= 2 * self.config["devices"]["chunksize"]:
            self.errorlist.append((["devices","target_level"], f"target_level can't be larger than {2 * self.config['devices']['chunksize']}"))



if __name__ == "__main__":
    file_validator = CamillaValidator()
    file_validator.validate_file(sys.argv[1])
    errors = file_validator.get_errors()
    warnings = file_validator.get_warnings()
    print("\nErrors:")
    for e in errors:
        print("/".join([str(p) for p in e[0]]), " : ",  e[1])
    print("\nWarnings:")
    for w in warnings:
        print("/".join([str(p) for p in w[0]]), " : ", w[1])






