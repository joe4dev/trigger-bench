# Development

Describes the development setup, implementation insights, challenges, etc.

## Install dependencies

```sh
make install
```

## Linting

```sh
make lint
```

## Tests

```sh
make test
# Selectively run unit or integration tests
make unit_test
make integration_test
```

## VSCode

* Example settings: [settings.sample.json](../.vscode/settings.sample.json). Change `python.pythonPath`
* Recommended plugins: [extensions.json](../.vscode/extensions.json)
* [Python testing in VSCode](https://code.visualstudio.com/docs/python/testing)

## Debugging

* Use the tests and local mode to debug
* Alternatively, an interactive Python shell can be used as breakpoint by inserting the following snippet into the code:

  ```py
  # Native
  import code; code.interact(local=dict(globals(), **locals()))
  # With ipdb (requires dev dependencies or pip install ipdb)
  import ipdb; ipdb.set_trace()
  ```

## Useful Python Tools

* [pip-check](https://pypi.org/project/pip-check/) gives you a quick overview of all installed packages and their update status.
* [pipdeptree](https://pypi.org/project/pipdeptree/) is a command line utility for displaying the installed python packages in form of a dependency tree.

## Design

* [DESIGN_V1](./DESIGN_V1.md)

## Troubleshooting

### lzma module missing

```none
packages/pandas/compat/__init__.py:124: UserWarning: Could not import the lzma module. Your installed Python is incomplete. Attempting to use lzma compression will result in a RuntimeError.
  warnings.warn(msg)
```

Some native dependencies are missing for a complete installation. See [this StackOverflow post](https://stackoverflow.com/a/58518449):

1. `brew install xz`
2. Reinstall Python `pyenv install 3.10.1`

### M1 ARM Support

The apigw_node app failed with the following error:

```none
INFO:root:docker=docker run --rm -v aws-secrets:/root/.aws -v '/Users/joe/Projects/Serverless/test-apps-yes/serverless-patterns/apigw-lambda-cdk/src':/apps/src --entrypoint='' node-cdk-apigw-node /bin/sh -c "cd '/apps/src' && cdk bootstrap aws://WARNING: The requested image's platform (linux/amd64) does not match the detected host platform (linux/arm64/v8) and no specific platform was requested
123456789012/eu-north-1"
INFO:run:/bin/sh: 2: Syntax error: Unterminated quoted string
```

We might need to detect the architecture on the host using cross-platform compatible Python and pass it into the Docker context to specify the architecture when running Docker commands. The first step would be to fix the Docker command and then adjust sb accordingly.
