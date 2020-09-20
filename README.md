SmartCitizen Data
=======

[![DOI](https://zenodo.org/badge/97752018.svg)](https://zenodo.org/badge/latestdoi/97752018)
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/fablabbcn/smartcitizen-data-framework/master?filepath=%2Fexamples%2Fnotebooks)

Welcome to the **SmartCitizen Data**. This is a framework built with many purposes, some of them being:

 - *Analysis*, *calibration* and *post-processing* of sensor data for development or performance assessment
 - *Unify* several sources of data and to *provide tools* for analysis in a standard way
 - *Tidy up* sensor data and allow for **traceability** of results and conclusions, and **reproducibility**
 - *Create visualisations* and reports in html format or print them as pdf

![](assets/images/saf_schema.png)

## Features


![](assets/images/covid-noise.png)

A full documentation of the framework is detailed in [the Smart Citizen Docs](https://docs.smartcitizen.me/Data%20Analysis/). Some examples in this repository include:

- Interacting with several sensors APIs
- Clean data, export and calculate metrics
- Model sensor data and calibrate sensors
- Generate data visualisations
- Generate analysis reports and upload them to [Zenodo](http://zenodo.org)

![](assets/images/Workflow.png)

## Funding

This work has received funding from the European Union's Horizon 2020 research and innovation program under the grant agreement [No. 689954](https://cordis.europa.eu/project/rcn/202639_en.html)

## Compatibility

Works with `Python 3.*`. It can be used with [JupyterLab](https://github.com/jupyterlab/jupyterlab) for data analysis, but it is not mandatory. There are plenty of examples in the `examples` folder. These are meant to show how to interface with the `python` code in the `scdata` folder.

## Installation

Simply clone the repository with:

```
git clone https://github.com/fablabbcn/smartcitizen-data-framework.git
cd smartcitizen-data-framework
```

Install `scdata` package with requirements:

```
python setup.py install
```

**NB**: maybe one day it will be in `pip`, but not yet.

### Tokens and config

If you want to upload data to [Zenodo](http://zenodo.org), you will need to fill set an environment variable called `ZENODO_TOKEN` in your environment.

You can get more instructions [here](https://docs.smartcitizen.me/Guides/Upload%20data%20to%20zenodo/).

A configuration file is available at `~/.config/scdata/config.yaml`, which contains a set of configurable variables to allow or not the local storage of relevant data in the data folder, normally in `~/.cache/scdata/data`:

```
data:
  cached_data_margin: 2
  load_cached_api: true
  reload_firmware_names: true
  store_cached_api: true
paths:
  config: /Users/username/.config/scdata
  data: /Users/username/.cache/scdata
  export: /Users/username/.cache/scdata/export
  interim: /Users/username/.cache/scdata/interim
  inventory: ''
  models: /Users/username/.cache/scdata/models
  processed: /Users/username/.cache/scdata/processed
  raw: /Users/username/.cache/scdata/raw
  reports: /Users/username/.cache/scdata/reports
  uploads: /Users/username/.cache/scdata/uploads
zenodo_real_base_url: https://zenodo.org
zenodo_sandbox_base_url: http://sandbox.zenodo.org
```

### Using with Jupyterlab (optional)

It can also be used with `jupyter lab` or `jupyter`. For this [install juypterlab](https://github.com/jupyterlab/jupyterlab) and (optionally), these extensions:

1. Notebook extensions configurator:

```
pip install jupyter_nbextensions_configurator
```

2. Plotly in jupyter lab (interactive plots):

```
jupyter labextension install jupyterlab-plotly
```

If using this option, examples on how to generate automatic reports from `jupyter notebooks` are also given in the examples folder.

## Contribute

Issues and PR more than welcome!
