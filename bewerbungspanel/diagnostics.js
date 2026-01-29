(function () {
    'use strict';

    // ==================== CSRF DIAGNOSTICS ====================

    /**
     * CSRF 403 Diagnostics Tool
     * Tests CSRF protection and provides detailed debug information
     * Exposed globally for admin panel access
     */
    window.diagnoseCSRF = async function () {
        const results = {
            timestamp: new Date().toISOString(),
            tests: [],
            summary: {}
        };

        console.log('🔍 Diagnosing 403 Forbidden errors...\n');

        // Test 1: Request WITHOUT CSRF token
        console.log('Test 1: Request without CSRF token...');
        try {
            const resp1 = await fetch('/api/applications', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    applicationType: 'staff',
                    roblox_user: 'DiagnoseTest',
                    discord_name: 'Test#0001',
                    age: 18,
                    about_me: 'Dies ist ein automatischer Test für die CSRF Diagnose Funktion.',
                    daily_time: '1h'
                })
            });

            const test1Result = {
                name: 'Request without CSRF token',
                status: resp1.status,
                expected: 403,
                passed: resp1.status === 403,
                message: resp1.status === 403 ? '✅ CSRF protection working' : '❌ CSRF protection FAILED'
            };

            results.tests.push(test1Result);
            console.log(`  → Status: ${resp1.status} ${test1Result.message}`);

        } catch (error) {
            results.tests.push({
                name: 'Request without CSRF token',
                status: 'ERROR',
                error: error.message,
                passed: false
            });
            console.error('  → Error:', error);
        }

        // Test 2: Check if CSRF token exists in DOM
        console.log('\nTest 2: CSRF token presence in DOM...');
        const token = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');

        const test2Result = {
            name: 'CSRF token in DOM',
            tokenFound: !!token,
            tokenPreview: token ? token.substring(0, 20) + '...' : 'NO TOKEN',
            passed: !!token,
            message: token ? '✅ Token found in DOM' : '❌ NO TOKEN IN DOM'
        };

        results.tests.push(test2Result);
        console.log(`  → Token found: ${test2Result.message}`);

        if (!token) {
            console.log('\n⚠️  PROBLEM: No CSRF token found in DOM!');
            console.log('   Solution: Add <meta name="csrf-token" content="..."> in HTML head');
            results.summary = {
                overallStatus: 'FAILED',
                issue: 'Missing CSRF token in DOM',
                recommendation: 'Add CSRF token meta tag to HTML'
            };
            return results;
        }

        // Test 3: Request WITH CSRF token
        console.log('\nTest 3: Request WITH CSRF token...');
        try {
            const resp3 = await fetch('/api/applications', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': token,
                    'X-Requested-With': 'DRP-Client'
                },
                body: JSON.stringify({
                    applicationType: 'staff',
                    roblox_user: 'DiagnoseTest2',
                    discord_name: 'Test2#0002',
                    age: 18,
                    about_me: 'Dies ist ein automatischer Test für die CSRF Diagnose Funktion.',
                    daily_time: '1h'
                })
            });

            const responseData = await resp3.json().catch(() => null);

            const test3Result = {
                name: 'Request WITH CSRF token',
                status: resp3.status,
                ok: resp3.ok,
                passed: resp3.ok || resp3.status === 400, // 400 could be validation error, which is OK
                response: responseData
            };

            results.tests.push(test3Result);
            console.log(`  → Status: ${resp3.status}`);

            if (resp3.status === 403) {
                console.log('\n🤔 Still 403 with token? Possible causes:');
                console.log('   1. Token validation logic is too strict');
                console.log('   2. IP-based blocking');
                console.log('   3. Additional auth requirements');
                console.log('   4. CORS issues');
                if (responseData) console.log('\n   Server response:', responseData);

                results.summary = {
                    overallStatus: 'FAILED',
                    issue: '403 even with valid token',
                    possibleCauses: ['Strict validation', 'IP blocking', 'Auth requirements', 'CORS'],
                    serverResponse: responseData
                };
            } else if (resp3.ok) {
                console.log('\n✅ Request accepted with token! CSRF is working correctly.');
                if (responseData) console.log('\n   Server response:', responseData);

                results.summary = {
                    overallStatus: 'SUCCESS',
                    message: 'CSRF protection is working correctly',
                    serverResponse: responseData
                };
            } else {
                console.log(`\n⚠️  Different error: ${resp3.status}`);
                if (responseData) console.log('\n   Server response:', responseData);

                results.summary = {
                    overallStatus: 'PARTIAL',
                    message: `Non-403 error: ${resp3.status}`,
                    note: 'CSRF may be working, but other validation failed',
                    serverResponse: responseData
                };
            }

        } catch (error) {
            results.tests.push({
                name: 'Request WITH CSRF token',
                status: 'ERROR',
                error: error.message,
                passed: false
            });
            console.error('  → Error:', error);

            results.summary = {
                overallStatus: 'ERROR',
                issue: 'Network or connection error',
                error: error.message
            };
        }

        console.log('\n' + '='.repeat(60));
        console.log('DIAGNOSTIC SUMMARY:', results.summary);
        console.log('='.repeat(60));

        return results;
    };

    console.log('✅ Diagnostics loaded');
})();
