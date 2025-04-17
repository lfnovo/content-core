# Using the Content Core Library

This documentation explains how to configure and use the **Content Core** library in your projects. The library allows customization of AI model settings through a YAML file and environment variables.

## Environment Variable for Configuration

The library uses the `CCORE_MODEL_CONFIG_PATH` environment variable to locate the custom YAML configuration file. If this variable is not set or the specified file is not found, the library will fall back to internal default settings.

To set the environment variable, add the following line to your `.env` file or set it directly in your environment:

```
CCORE_MODEL_CONFIG_PATH=/path/to/your/models_config.yaml
```

## YAML File Schema

The YAML configuration file defines the AI models that the library will use. The structure of the file is as follows:

- **speech_to_text**: Configuration for the speech-to-text model.
  - **provider**: Model provider (example: `openai`).
  - **model_name**: Model name (example: `whisper-1`).
- **default_model**: Configuration for the default language model.
  - **provider**: Model provider.
  - **model_name**: Model name.
  - **config**: Additional parameters like `temperature`, `top_p`, `max_tokens`.
- **cleanup_model**: Configuration for the content cleanup model.
  - **provider**: Model provider.
  - **model_name**: Model name.
  - **config**: Additional parameters.
- **summary_model**: Configuration for the summary model.
  - **provider**: Model provider.
  - **model_name**: Model name.
  - **config**: Additional parameters.

### Default YAML File

Here is the content of the default YAML file used by the library:

```yaml
speech_to_text:
  provider: openai
  model_name: whisper-1

default_model:
  provider: openai
  model_name: gpt-4o-mini
  config:
    temperature: 0.5
    top_p: 1
    max_tokens: 2000

cleanup_model:
  provider: openai
  model_name: gpt-4o-mini
  config:
    temperature: 0
    max_tokens: 8000
    output_format: json

summary_model:
  provider: openai
  model_name: gpt-4o-mini
  config:
    temperature: 0
    top_p: 1
    max_tokens: 2000
```

## Customization

You can customize any aspect of the YAML file to suit your needs. Change the providers, model names, or configuration parameters as desired.

To simplify setup, we suggest copying the provided sample files:
- Copy `.env.sample` to `.env` and adjust the environment variables, including `CCORE_MODEL_CONFIG_PATH`.
- Copy `models_config.yaml.sample` to your desired location and modify it as needed.

This will allow you to quickly start with customized settings without needing to create the files from scratch.

## Support

If you have questions or encounter issues while using the library, open an issue in the repository or contact the support team.
