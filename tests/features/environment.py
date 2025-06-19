# -- FILE: environment.py
from behave.model import Scenario
from tests.steps.database_test_utils import before_scenario, after_scenario, before_all, after_all

def before_all(context):
    """Set up environment before all tests."""
    before_all(context)

def after_all(context):
    """Clean up environment after all tests."""
    after_all(context)

def before_scenario(context, scenario):
    """Set up environment before each scenario."""
    before_scenario(context, scenario)

def after_scenario(context, scenario):
    """Clean up environment after each scenario."""
    after_scenario(context, scenario)

def before_feature(context, feature):
    """Set up environment before each feature."""
    # Add any feature-specific setup here
    pass

def after_feature(context, feature):
    """Clean up environment after each feature."""
    # Add any feature-specific cleanup here
    pass

def before_tag(context, tag):
    """Run code based on specific tags."""
    # Add any tag-specific setup here if needed
    if tag == 'performance':
        print("Running performance test - ensure system is not under heavy load")
    elif tag == 'reliability':
        print("Running reliability test - may involve error injection")
    elif tag == 'security':
        print("Running security test - checking for vulnerabilities")
    elif tag == 'scalability':
        print("Running scalability test - testing with large data volumes")
