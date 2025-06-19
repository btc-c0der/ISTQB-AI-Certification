#!/usr/bin/env python3
"""
Run all non-functional BDD tests for the database module.
"""
import os
import sys
import subprocess
import argparse
import datetime

def print_header(message):
    """Print a header message."""
    print("\n" + "=" * 80)
    print(f" {message} ".center(80))
    print("=" * 80 + "\n")

def run_tests(args):
    """Run the tests with the specified options."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tests_dir = os.path.join(base_dir, 'tests')
    features_dir = os.path.join(tests_dir, 'features')
    
    # Ensure we have the features directory
    if not os.path.exists(features_dir):
        print(f"Error: Features directory not found at {features_dir}")
        sys.exit(1)
    
    # Build command
    cmd = ['behave']
    
    # Add features directory
    cmd.append(features_dir)
    
    # Add tags filter if specified
    if args.tags:
        cmd.extend(['--tags', args.tags])
    
    # Add format option
    if args.format:
        cmd.extend(['--format', args.format])
    
    # Add output file if specified
    if args.output:
        cmd.extend(['--outfile', args.output])
    
    # Add verbosity
    if args.verbose:
        cmd.append('--verbose')
    
    # Add other options
    if args.junit:
        cmd.extend(['--junit', '--junit-directory', 'reports/junit'])
    
    if args.no_capture:
        cmd.append('--no-capture')
    
    if args.stop:
        cmd.append('--stop')
    
    # Add specific features if specified
    if args.features:
        # Replace with the full paths
        cmd = [cmd[0]]  # Keep 'behave'
        for feature in args.features:
            if not feature.endswith('.feature'):
                feature += '.feature'
            feature_path = os.path.join(features_dir, feature)
            if os.path.exists(feature_path):
                cmd.append(feature_path)
            else:
                print(f"Warning: Feature file not found: {feature_path}")
    
    # Create output directories if needed
    if args.output:
        output_dir = os.path.dirname(args.output)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
    
    if args.junit:
        junit_dir = 'reports/junit'
        if not os.path.exists(junit_dir):
            os.makedirs(junit_dir)
    
    # Print the command being run
    print("Running command:", ' '.join(cmd))
    
    # Run the tests
    return subprocess.call(cmd)

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Run non-functional BDD tests for the database module.')
    
    # Test selection
    parser.add_argument('--tags', help='Only run features/scenarios with these tags (e.g., "performance")')
    parser.add_argument('--features', nargs='+', help='Specify feature files to run')
    
    # Output options
    parser.add_argument('--format', default='pretty', 
                        choices=['pretty', 'plain', 'json', 'junit'],
                        help='Output format')
    parser.add_argument('--output', help='Output file')
    parser.add_argument('--junit', action='store_true', help='Generate JUnit XML reports')
    
    # Behavior options
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--no-capture', action='store_true', help="Don't capture stdout/stderr")
    parser.add_argument('--stop', action='store_true', help='Stop on first failure')
    
    args = parser.parse_args()
    
    # Default output filename if not specified but format is
    if args.format != 'pretty' and not args.output:
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        args.output = f'reports/bdd_test_report_{timestamp}.{args.format}'
    
    # Print header
    print_header("Database Non-Functional Tests")
    
    # Run the tests
    result = run_tests(args)
    
    # Print summary
    if result == 0:
        print_header("All tests passed!")
    else:
        print_header(f"Tests completed with return code {result}")
    
    return result

if __name__ == '__main__':
    sys.exit(main())
