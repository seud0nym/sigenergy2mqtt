"""
This file is required by pytest to treat the directory as a package.
It ensures that test files with the same name across different domain 
sub-directories (e.g., test_service.py) do not cause import conflicts 
during module collection and test discovery.
"""
