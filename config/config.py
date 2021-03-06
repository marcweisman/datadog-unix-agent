# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import os
import yaml
import logging
import decimal
from collections import defaultdict

from .providers import ConfigProvider


log = logging.getLogger(__name__)


class Config(object):

    DEFAULT_CONF_NAME = "datadog.yaml"
    DEFAULT_ENV_PREFIX = "DD_"

    def __init__(self, conf_name=DEFAULT_CONF_NAME, env_prefix=DEFAULT_ENV_PREFIX):
        self.search_paths = set()
        self.conf_name = conf_name
        self.env_prefix = env_prefix
        self.env_bindings = set()
        self.data = {}
        self.defaults = {}

        self._providers = {}
        self._check_configs = defaultdict(dict)

    def __getitem__(self, key):
        try:
            ret = self.data[key]
        except KeyError:
            ret = self.defaults[key]

        return ret

    def __setitem__(self, key, value):
        self.set(key, value)

    def __delitem__(self, key):
        self.reset(key)

    def set_default(self, key, value):
        self.defaults[key] = value

    def set(self, key, value):
        self.data[key] = value

    def reset(self, key):
        del self.data[key]

    def get(self, key, default=None):
        return self.data.get(key, self.defaults.get(key, default))

    def add_search_path(self, search_path):
        self.search_paths.add(search_path)

    def load(self):
        if self.search_paths:
            for path in self.search_paths:
                conf_path = os.path.join(path, self.conf_name)
                if os.path.isfile(conf_path):
                    with open(conf_path, "r") as f:
                        self.data = yaml.load(f)
                    break
            else:
                log.error("Could not find %s in search_paths: %s", self.conf_name, self.search_paths)

        for env_var in self.env_bindings:
            key = self.env_prefix + env_var
            if key in os.environ:
                self.data[env_var] = os.environ[key]
            elif key.upper() in os.environ:
                self.data[env_var] = os.environ[key.upper()]

        self.validate()

    def bind_env(self, key):
        self.env_bindings.add(key)

    def bind_env_and_set_default(self, key, value):
        self.bind_env(key)
        self.set_default(key, value)

    def validate(self):
        self.validate_histogram_aggregates()
        self.validate_histogram_percentiles()

    def validate_histogram_aggregates(self):
        aggregates_config = self.data.get('histogram_aggregates')

        if not aggregates_config:
            return
        if aggregates_config and not isinstance(aggregates_config, list):
            log.exception("histogram_aggregates should be a list - ignoring")
            self.data.pop('histogram_aggregates')
            return

        result = []
        valid_values = ['min', 'max', 'median', 'avg', 'sum', 'count']

        for val in aggregates_config:
            try:
                val = val.strip()
                if val not in valid_values:
                    log.warning("Ignored histogram aggregate {0}, invalid".format(val))
                    continue
                else:
                    result.append(val)
            except Exception:
                log.exception("Error when parsing histogram aggregate {0}, invalid".format(val))

        self.data['histogram_aggregates'] = result

    def validate_histogram_percentiles(self):
        percentiles_config = self.data.get('histogram_percentiles')

        if not percentiles_config:
            return
        elif percentiles_config and not isinstance(percentiles_config, list):
            log.exception("histogram_percentiles should be a list - ignoring")
            self.data.pop('histogram_percentiles')
            return

        result = []
        for val in percentiles_config:
            try:
                if isinstance(val, basestring):
                    val = val.strip()
                floatval = float(val)
                if floatval <= 0 or floatval >= 1:
                    raise ValueError

                if str(floatval)[::-1].find('.') > 2:
                    # round to two decimal places
                    floatval = float(
                        decimal.Decimal(floatval).quantize(
                            decimal.Decimal('.01'), rounding=decimal.ROUND_DOWN)
                    )
                result.append(floatval)
            except ValueError:
                log.warning("Bad histogram percentile value {0}, must be float in ]0;1[, skipping"
                            .format(val))
            except Exception:
                log.exception("Error when parsing histogram percentiles, skipping")
                return None

        self.data['histogram_percentiles'] = result

    def add_provider(self, source, provider):
        """ Adds ConfigProvider for check configurations """
        if not isinstance(provider, ConfigProvider):
            raise ValueError("expected a configuration provider")

        self._providers[source] = provider

    def collect_check_configs(self):
        """ Iterates providers collecting configurations """
        for source, provider in self._providers.iteritems():
            checksconfigs = provider.collect()
            for check, configs in checksconfigs.iteritems():
                current_configs = self._check_configs[source].get(check, [])
                for config in configs:
                    if config in current_configs:
                        # skip existing ones in case we re-call this
                        continue

                    current_configs.append(config)

                self._check_configs[source][check] = current_configs

    def get_check_configs(self):
        return self._check_configs
