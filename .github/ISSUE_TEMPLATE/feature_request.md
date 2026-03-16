name: Feature Request | 功能请求
description: Suggest a new feature or improvement | 建议新功能或改进
title: "[FEATURE] "
labels: ["enhancement"]

body:
  - type: markdown
    attributes:
      value: |
        🎉 感谢你的建议！请告诉我们你想要什么新功能。
        Thank you for your suggestion! Please tell us what new feature you'd like to see.

  - type: textarea
    id: problem
    attributes:
      label: Problem Statement | 问题描述
      description: Is your feature request related to a problem? Describe it.
      placeholder: "I'm always frustrated when..."
    validations:
      required: true

  - type: textarea
    id: solution
    attributes:
      label: Proposed Solution | 建议方案
      description: Describe the solution you'd like
      placeholder: "It would be helpful if..."
    validations:
      required: true

  - type: textarea
    id: alternatives
    attributes:
      label: Alternative Solutions | 替代方案
      description: Describe alternative solutions or features you've considered
      placeholder: "Other ways to solve this..."

  - type: textarea
    id: use_case
    attributes:
      label: Use Case | 使用场景
      description: Describe your use case for this feature
      placeholder: "I want to use this for..."

  - type: dropdown
    id: impact
    attributes:
      label: Impact | 影响范围
      description: How important is this feature?
      options:
        - Must have | 必须有
        - Nice to have | 好有
        - Can wait | 可以等
    validations:
      required: true

  - type: dropdown
    id: complexity
    attributes:
      label: Estimated Complexity | 估计难度
      description: How complex do you think this feature would be?
      options:
        - Easy | 简单
        - Medium | 中等
        - Hard | 困难
        - Very Hard | 非常困难

  - type: textarea
    id: additional
    attributes:
      label: Additional Information | 附加信息
      description: Any additional context or resources
      placeholder: "Links to related issues, discussions, etc."

  - type: checkboxes
    id: checklist
    attributes:
      label: Checklist | 检查项
      options:
        - label: I have searched for similar feature requests | 我已搜索类似功能请求
          required: true
        - label: This feature aligns with the project goals | 此功能符合项目目标
          required: false
