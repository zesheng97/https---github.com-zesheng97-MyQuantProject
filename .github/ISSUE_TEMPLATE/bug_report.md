name: Bug Report | Bug 报告
description: Report a bug to help us improve | 报告 Bug 帮助我们改进
title: "[BUG] "
labels: ["bug"]

body:
  - type: markdown
    attributes:
      value: |
        感谢你报告这个问题！为了帮助我们快速定位和解决 Bug，请填写以下信息。
        Thank you for reporting! Please fill in the following to help us quickly fix the issue.

  - type: textarea
    id: description
    attributes:
      label: Bug Description | Bug 描述
      description: Clear and concise description of what the bug is
      placeholder: "Example: The backtest crashes when..."
    validations:
      required: true

  - type: textarea
    id: repro
    attributes:
      label: Steps to Reproduce | 复现步骤
      description: Steps to reproduce the behavior
      value: |
        1. Go to...
        2. Click on...
        3. See error...
    validations:
      required: true

  - type: textarea
    id: expected
    attributes:
      label: Expected Behavior | 预期行为
      description: What should happen instead?
      placeholder: "The backtest should complete successfully and return metrics"
    validations:
      required: true

  - type: textarea
    id: actual
    attributes:
      label: Actual Behavior | 实际行为
      description: What actually happens?
      placeholder: "Error message or unexpected behavior"
    validations:
      required: true

  - type: textarea
    id: error_log
    attributes:
      label: Error Log | 错误日志
      description: If applicable, please paste the full error traceback
      render: python

  - type: dropdown
    id: environment
    attributes:
      label: Environment | 环境
      options:
        - Windows 10/11
        - macOS
        - Linux
        - Other
    validations:
      required: true

  - type: textarea
    id: system_info
    attributes:
      label: System Information | 系统信息
      description: Please provide your environment details
      value: |
        - Python version: 3.10 / 3.11 / 3.12
        - Personal Quant Lab version: 2026.0.0
        - Key dependencies: pandas, yfinance, streamlit version
        - OS: Windows / macOS / Linux
    validations:
      required: true

  - type: textarea
    id: additional
    attributes:
      label: Additional Information | 附加信息
      description: Any additional context, screenshots, or files
      placeholder: "Screenshots, configuration files, etc."

  - type: checkboxes
    id: checklist
    attributes:
      label: Checklist | 检查项
      description: Please make sure you have checked the following
      options:
        - label: I have searched existing issues | 我已搜索现有 Issue
          required: true
        - label: I have updated to the latest version | 我已更新到最新版本
          required: false
        - label: I can reproduce this issue consistently | 我能持续复现此问题
          required: true
