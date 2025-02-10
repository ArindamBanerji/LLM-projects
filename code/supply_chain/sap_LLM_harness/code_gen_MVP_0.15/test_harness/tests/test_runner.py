"""
Complete test runner implementation for SAP Test Harness MVP 0.1.
Provides unified test execution for all test types with state management.

Part 1: Core classes and main TestRunner implementation
"""

import asyncio
import inspect
import traceback
import time
import logging
import json
from typing import Dict, Any, List, Optional, Type, Union, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

class TestType(Enum):
    """Test type enumeration"""
    MATERIAL = "material"
    STATE = "state"
    P2P = "p2p"
    ERROR = "error"
    MULTI_DOC = "multi_doc"
    CONSOLIDATED = "consolidated"

@dataclass
class TestConfig:
    """Test configuration settings"""
    verbose: bool = True
    save_state: bool = False
    include_timing: bool = True
    state_snapshots: bool = False
    error_focus: bool = False
    multi_doc: bool = False
    consolidated: bool = False
    log_level: str = "INFO"
    reset_state: bool = True

@dataclass
class TestResult:
    """Individual test result"""
    name: str
    success: bool
    execution_time: float
    error: Optional[str] = None
    state_snapshot: Optional[Dict] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    details: Optional[Dict[str, Any]] = None

@dataclass
class TestSuiteResult:
    """Complete test suite results"""
    total_tests: int
    passed_tests: int
    failed_tests: int
    execution_time: float
    results: List[TestResult]
    state_snapshots: Optional[List[Dict]] = None
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    success_rate: float = field(init=False)
    test_names: Set[str] = field(default_factory=set)

    def __post_init__(self):
        """Calculate success rate and collect test names"""
        self.success_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0.0
        self.test_names = {result.name for result in self.results}

    def get_failed_tests(self) -> List[TestResult]:
        """Get list of failed tests"""
        return [result for result in self.results if not result.success]

class TestRunner:
    """Test runner implementation"""
    
    def __init__(self, config: TestConfig):
        """Initialize test runner with configuration"""
        self.config = config
        self.logger = self._setup_logger()
        self._state_history: List[Dict[str, Any]] = []
        self._current_state: Optional[Dict[str, Any]] = None

    def _setup_logger(self) -> logging.Logger:
        """Configure logging"""
        logger = logging.getLogger(f"TestRunner-{id(self)}")
        logger.setLevel(getattr(logging, self.config.log_level))
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger

    async def run_test_suite(self, test_class: Type) -> TestSuiteResult:
        """
        Run complete test suite for given test class
        
        Args:
            test_class: Test class to execute
            
        Returns:
            TestSuiteResult: Complete test execution results
        """
        start_time = time.time()
        results: List[TestResult] = []
        passed = 0
        failed = 0
        state_snapshots = [] if self.config.state_snapshots else None
        
        try:
            # Create test instance
            test_instance = test_class()
            self.logger.info(f"Starting test suite: {test_class.__name__}")
            
            # Get test methods
            test_methods = self._get_test_methods(test_instance)
            self.logger.info(f"Found {len(test_methods)} test methods")
            
            # Execute each test
            for method_name in test_methods:
                result = await self._execute_test_method(
                    test_instance, 
                    method_name,
                    state_snapshots
                )
                results.append(result)
                if result.success:
                    passed += 1
                else:
                    failed += 1
                
                # Reset state if configured
                if self.config.reset_state:
                    self._current_state = None
            
        except Exception as e:
            self.logger.error(f"Test suite execution failed: {str(e)}")
            self.logger.error(traceback.format_exc())
            
        finally:
            execution_time = time.time() - start_time
            suite_result = TestSuiteResult(
                total_tests=len(results),
                passed_tests=passed,
                failed_tests=failed,
                execution_time=execution_time,
                results=results,
                state_snapshots=state_snapshots
            )
            
            self._log_suite_results(suite_result)
            return suite_result

    async def _execute_test_method(
        self, 
        instance: Any, 
        method_name: str,
        state_snapshots: Optional[List[Dict]]
    ) -> TestResult:
        """Execute single test method"""
        self.logger.info(f"Executing test: {method_name}")
        test_start = time.time()
        state_before = None
        state_after = None
        
        try:
            # Run setUp and capture initial state
            await self._run_setup(instance)
            if self.config.save_state and hasattr(instance, 'get_state'):
                state_before = instance.get_state()
            
            # Execute test
            method = getattr(instance, method_name)
            if inspect.iscoroutinefunction(method):
                await method()
            else:
                method()
            
            # Capture final state
            if self.config.save_state and hasattr(instance, 'get_state'):
                state_after = instance.get_state()
                if state_snapshots is not None:
                    state_snapshots.append({
                        'test': method_name,
                        'state': state_after,
                        'timestamp': datetime.now().isoformat()
                    })
            
            execution_time = time.time() - test_start
            if self.config.verbose:
                self.logger.info(f"{method_name}: PASSED ({execution_time:.3f}s)")
            
            return TestResult(
                name=method_name,
                success=True,
                execution_time=execution_time,
                state_snapshot=state_after,
                details={
                    'state_before': state_before,
                    'state_after': state_after
                }
            )
            
        except Exception as e:
            execution_time = time.time() - test_start
            error_msg = f"{type(e).__name__}: {str(e)}"
            
            if self.config.verbose:
                self.logger.error(f"{method_name}: FAILED ({execution_time:.3f}s)")
                self.logger.error(f"Error: {error_msg}")
                self.logger.error(traceback.format_exc())
            
            # Capture error state
            error_state = None
            if self.config.save_state and hasattr(instance, 'get_state'):
                try:
                    error_state = instance.get_state()
                except Exception as state_e:
                    self.logger.error(f"Failed to capture error state: {str(state_e)}")
            
            return TestResult(
                name=method_name,
                success=False,
                execution_time=execution_time,
                error=error_msg,
                state_snapshot=error_state,
                details={
                    'state_before': state_before,
                    'state_after': error_state,
                    'error_traceback': traceback.format_exc()
                }
            )
        
        finally:
            try:
                await self._run_teardown(instance)
            except Exception as e:
                self.logger.error(f"Teardown failed: {str(e)}")
            await asyncio.sleep(0.1)

    async def _run_setup(self, instance: Any) -> None:
        """Run setup if available"""
        if hasattr(instance, 'setUp'):
            try:
                self.logger.info("Running setUp")
                if inspect.iscoroutinefunction(instance.setUp):
                    await instance.setUp()
                else:
                    instance.setUp()
            except Exception as e:
                self.logger.error(f"setUp failed: {str(e)}")
                raise

    async def _run_teardown(self, instance: Any) -> None:
        """Run teardown if available"""
        if hasattr(instance, 'tearDown'):
            try:
                self.logger.info("Running tearDown")
                if inspect.iscoroutinefunction(instance.tearDown):
                    await instance.tearDown()
                else:
                    instance.tearDown()
            except Exception as e:
                self.logger.error(f"tearDown failed: {str(e)}")
                raise

    def _get_test_methods(self, instance: Any) -> List[str]:
        """Get all test methods from instance"""
        return sorted([
            method[0] for method in inspect.getmembers(instance, predicate=inspect.ismethod)
            if method[0].startswith('test_')
        ])

    def _log_suite_results(self, results: TestSuiteResult) -> None:
        """Log test suite results"""
        self.logger.info("\nTest Suite Results:")
        self.logger.info("=" * 50)
        self.logger.info(f"Total Tests    : {results.total_tests}")
        self.logger.info(f"Tests Passed   : {results.passed_tests}")
        self.logger.info(f"Tests Failed   : {results.failed_tests}")
        self.logger.info(f"Success Rate   : {results.success_rate:.1f}%")
        self.logger.info(f"Execution Time : {results.execution_time:.3f}s")
        
        if results.failed_tests > 0:
            self.logger.info("\nFailed Tests:")
            for result in results.get_failed_tests():
                self.logger.error(f"\n{result.name}:")
                self.logger.error(f"Error: {result.error}")
                if result.details and result.details.get('error_traceback'):
                    self.logger.error("Traceback:")
                    self.logger.error(result.details['error_traceback'])
                    
"""
Complete test runner implementation for SAP Test Harness MVP 0.1.
Part 2: Consolidated test runner and utility functions
"""

async def run_consolidated_tests(
    test_classes: List[Type],
    verbose: bool = True,
    include_timing: bool = True,
    save_state: bool = True,
    **kwargs
) -> Dict[str, TestSuiteResult]:
    """
    Run tests for multiple test classes and aggregate results
    
    Args:
        test_classes: List of test classes to execute
        verbose: Enable verbose output
        include_timing: Include timing information
        save_state: Save state snapshots
        **kwargs: Additional configuration options
        
    Returns:
        Dict mapping test class names to their TestSuiteResults
    """
    results: Dict[str, TestSuiteResult] = {}
    start_time = time.time()
    
    config = TestConfig(
        verbose=verbose,
        save_state=save_state,
        include_timing=include_timing,
        consolidated=True,
        **kwargs
    )
    
    for test_class in test_classes:
        class_name = test_class.__name__
        
        # Create runner for this test class
        runner = TestRunner(config)
        
        try:
            # Run test suite
            suite_result = await runner.run_test_suite(test_class)
            results[class_name] = suite_result
            
            if verbose:
                logging.info(f"\nResults for {class_name}:")
                logging.info("-" * 50)
                logging.info(f"Total Tests    : {suite_result.total_tests}")
                logging.info(f"Tests Passed   : {suite_result.passed_tests}")
                logging.info(f"Tests Failed   : {suite_result.failed_tests}")
                logging.info(f"Success Rate   : {suite_result.success_rate:.1f}%")
                if include_timing:
                    logging.info(f"Execution Time : {suite_result.execution_time:.3f}s")
            
        except Exception as e:
            logging.error(f"Failed to run {class_name}: {str(e)}")
            logging.error(traceback.format_exc())
    
    # Log consolidated summary
    if verbose:
        total_tests = sum(r.total_tests for r in results.values())
        total_passed = sum(r.passed_tests for r in results.values())
        total_time = time.time() - start_time
        
        logging.info("\nConsolidated Test Results:")
        logging.info("=" * 50)
        logging.info(f"Total Test Classes: {len(test_classes)}")
        logging.info(f"Total Tests       : {total_tests}")
        logging.info(f"Total Passed      : {total_passed}")
        logging.info(f"Total Failed      : {total_tests - total_passed}")
        logging.info(f"Overall Success   : {(total_passed/total_tests*100):.1f}%")
        logging.info(f"Total Time        : {total_time:.3f}s")
    
    return results

def create_runner(test_type: TestType, **kwargs) -> TestRunner:
    """
    Create configured test runner
    
    Args:
        test_type: Type of tests to run
        **kwargs: Additional configuration options
        
    Returns:
        Configured TestRunner instance
    """
    # Set type-specific defaults
    if test_type == TestType.STATE:
        kwargs['save_state'] = True
        kwargs['state_snapshots'] = True
    elif test_type == TestType.ERROR:
        kwargs['error_focus'] = True
        kwargs['save_state'] = True
    elif test_type == TestType.MULTI_DOC:
        kwargs['multi_doc'] = True
        kwargs['save_state'] = True
    elif test_type == TestType.P2P:
        kwargs['save_state'] = True
        kwargs['reset_state'] = True
    elif test_type == TestType.CONSOLIDATED:
        kwargs['consolidated'] = True
        kwargs['save_state'] = True
        kwargs['reset_state'] = True
        kwargs['state_snapshots'] = True
    
    config = TestConfig(**kwargs)
    return TestRunner(config)

async def run_material_tests(
    test_class: Type,
    **kwargs
) -> TestSuiteResult:
    """
    Run material management tests
    
    Args:
        test_class: Test class to execute
        **kwargs: Additional configuration options
        
    Returns:
        Test execution results
    """
    runner = create_runner(TestType.MATERIAL, **kwargs)
    return await runner.run_test_suite(test_class)

async def run_state_tests(
    test_class: Type,
    **kwargs
) -> TestSuiteResult:
    """
    Run state management tests
    
    Args:
        test_class: Test class to execute
        **kwargs: Additional configuration options
        
    Returns:
        Test execution results
    """
    runner = create_runner(TestType.STATE, **kwargs)
    return await runner.run_test_suite(test_class)

async def run_p2p_tests(
    test_class: Type,
    **kwargs
) -> TestSuiteResult:
    """
    Run P2P process tests
    
    Args:
        test_class: Test class to execute
        **kwargs: Additional configuration options
        
    Returns:
        Test execution results
    """
    runner = create_runner(TestType.P2P, **kwargs)
    return await runner.run_test_suite(test_class)

async def run_error_tests(
    test_class: Type,
    **kwargs
) -> TestSuiteResult:
    """
    Run error case tests
    
    Args:
        test_class: Test class to execute
        **kwargs: Additional configuration options
        
    Returns:
        Test execution results
    """
    runner = create_runner(TestType.ERROR, **kwargs)
    return await runner.run_test_suite(test_class)

async def run_multi_doc_tests(
    test_class: Type,
    **kwargs
) -> TestSuiteResult:
    """
    Run multi-document tests
    
    Args:
        test_class: Test class to execute
        **kwargs: Additional configuration options
        
    Returns:
        Test execution results
    """
    runner = create_runner(TestType.MULTI_DOC, **kwargs)
    return await runner.run_test_suite(test_class)