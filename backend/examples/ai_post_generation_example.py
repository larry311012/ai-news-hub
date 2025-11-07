"""
AI Post Generation Service - Usage Examples

This script demonstrates how to use the AI post generation service
with various scenarios and configurations.
"""
import asyncio
import os
from typing import List, Dict

# Set up paths for imports
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from services.ai_post_generation_service import AIPostGenerationService


# Sample articles for testing
SAMPLE_ARTICLES = [
    {
        'id': 1,
        'title': 'Breakthrough in Natural Language Processing',
        'summary': 'Researchers achieve 95% accuracy in multilingual translation using new transformer architecture',
        'link': 'https://example.com/nlp-breakthrough',
        'source': 'AI Research Weekly',
        'published': '2024-01-15T10:00:00'
    },
    {
        'id': 2,
        'title': 'Machine Learning Applications in Healthcare',
        'summary': 'New ML models detect diseases earlier with 90% accuracy, transforming patient care',
        'link': 'https://example.com/ml-healthcare',
        'source': 'Health Tech News',
        'published': '2024-01-16T14:30:00'
    },
    {
        'id': 3,
        'title': 'Ethical AI: Balancing Innovation and Responsibility',
        'summary': 'Industry leaders discuss frameworks for responsible AI development and deployment',
        'link': 'https://example.com/ethical-ai',
        'source': 'Tech Ethics Journal',
        'published': '2024-01-17T09:15:00'
    }
]


async def example_1_basic_generation():
    """
    Example 1: Basic post generation for single platform
    """
    print("\n" + "="*60)
    print("Example 1: Basic Post Generation (Twitter)")
    print("="*60)

    # Initialize service with OpenAI
    api_key = os.getenv("OPENAI_API_KEY", "your-api-key-here")
    service = AIPostGenerationService(api_key=api_key, provider="openai")

    try:
        # Generate Twitter post
        result = await service.generate_post(
            articles=SAMPLE_ARTICLES[:2],  # Use first 2 articles
            platform="twitter",
            user_id=1,
            use_cache=False  # Force fresh generation
        )

        print(f"\n✅ Generation Successful!")
        print(f"Platform: {result['platform']}")
        print(f"Generation Time: {result['generation_time']}s")
        print(f"Cached: {result['cached']}")
        print(f"Remaining Requests: {result['remaining_requests']}")
        print(f"\nGenerated Content:")
        print("-" * 60)
        print(result['content'])
        print("-" * 60)
        print(f"\nMetadata:")
        print(f"  Provider: {result['metadata']['provider']}")
        print(f"  Model: {result['metadata']['model']}")
        print(f"  Total Tokens: {result['metadata']['total_tokens']}")

    except Exception as e:
        print(f"❌ Error: {str(e)}")


async def example_2_multi_platform():
    """
    Example 2: Generate posts for multiple platforms concurrently
    """
    print("\n" + "="*60)
    print("Example 2: Multi-Platform Generation")
    print("="*60)

    api_key = os.getenv("OPENAI_API_KEY", "your-api-key-here")
    service = AIPostGenerationService(api_key=api_key, provider="openai")

    try:
        # Generate for all platforms
        platforms = ["twitter", "linkedin", "instagram", "threads"]

        result = await service.generate_multi_platform(
            articles=SAMPLE_ARTICLES,
            platforms=platforms,
            user_id=1,
            tone="professional",
            use_cache=True
        )

        print(f"\n✅ Multi-Platform Generation Complete!")
        print(f"Success Count: {result['success_count']}")
        print(f"Error Count: {result['error_count']}")

        # Show results for each platform
        for platform, platform_result in result['results'].items():
            print(f"\n{platform.upper()}:")
            print(f"  Length: {len(platform_result['content'])} chars")
            print(f"  Cached: {platform_result['cached']}")
            print(f"  Time: {platform_result['generation_time']}s")
            print(f"  Content: {platform_result['content'][:80]}...")

        # Show errors if any
        if result['errors']:
            print("\n⚠️ Errors:")
            for platform, error in result['errors'].items():
                print(f"  {platform}: {error}")

    except Exception as e:
        print(f"❌ Error: {str(e)}")


async def example_3_custom_tone():
    """
    Example 3: Generate posts with custom tone
    """
    print("\n" + "="*60)
    print("Example 3: Custom Tone Generation")
    print("="*60)

    api_key = os.getenv("OPENAI_API_KEY", "your-api-key-here")
    service = AIPostGenerationService(api_key=api_key, provider="openai")

    tones = ["professional", "casual", "engaging"]

    for tone in tones:
        try:
            result = await service.generate_post(
                articles=SAMPLE_ARTICLES[:1],
                platform="linkedin",
                user_id=1,
                tone=tone,
                use_cache=False
            )

            print(f"\n{tone.upper()} Tone:")
            print("-" * 60)
            print(result['content'][:200] + "...")
            print("-" * 60)

        except Exception as e:
            print(f"❌ Error with {tone} tone: {str(e)}")


async def example_4_cache_demonstration():
    """
    Example 4: Demonstrate caching functionality
    """
    print("\n" + "="*60)
    print("Example 4: Cache Demonstration")
    print("="*60)

    api_key = os.getenv("OPENAI_API_KEY", "your-api-key-here")
    service = AIPostGenerationService(api_key=api_key, provider="openai")

    try:
        # First generation (cache miss)
        print("\n1st Generation (cache miss):")
        result1 = await service.generate_post(
            articles=SAMPLE_ARTICLES[:1],
            platform="twitter",
            user_id=1,
            use_cache=True
        )
        print(f"  Time: {result1['generation_time']}s")
        print(f"  Cached: {result1['cached']}")

        # Second generation (cache hit)
        print("\n2nd Generation (cache hit):")
        result2 = await service.generate_post(
            articles=SAMPLE_ARTICLES[:1],
            platform="twitter",
            user_id=1,
            use_cache=True
        )
        print(f"  Time: {result2['generation_time']}s")
        print(f"  Cached: {result2['cached']}")

        print(f"\n✅ Speed improvement: {result1['generation_time'] / max(result2['generation_time'], 0.01):.1f}x faster")

        # Content should be identical
        if result1['content'] == result2['content']:
            print("✅ Cache consistency verified (content matches)")

    except Exception as e:
        print(f"❌ Error: {str(e)}")


async def example_5_content_validation():
    """
    Example 5: Content validation
    """
    print("\n" + "="*60)
    print("Example 5: Content Validation")
    print("="*60)

    api_key = os.getenv("OPENAI_API_KEY", "your-api-key-here")
    service = AIPostGenerationService(api_key=api_key, provider="openai")

    test_cases = [
        {
            "platform": "twitter",
            "content": "Great article on AI! #AI #MachineLearning",
            "expected": "valid"
        },
        {
            "platform": "twitter",
            "content": "A" * 300,  # Too long
            "expected": "invalid"
        },
        {
            "platform": "instagram",
            "content": " ".join([f"#tag{i}" for i in range(35)]),  # Too many hashtags
            "expected": "invalid"
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}: {test_case['platform'].upper()}")

        result = await service.validate_content(
            content=test_case['content'],
            platform=test_case['platform']
        )

        print(f"  Is Valid: {result['is_valid']}")
        print(f"  Length: {result['content_length']}/{result['max_length']}")

        if result['warnings']:
            print(f"  Warnings: {', '.join(result['warnings'])}")

        if result['errors']:
            print(f"  Errors: {', '.join(result['errors'])}")

        # Verify expectation
        expected_valid = test_case['expected'] == "valid"
        if result['is_valid'] == expected_valid:
            print("  ✅ Validation result matches expectation")
        else:
            print("  ❌ Validation result doesn't match expectation")


async def example_6_rate_limiting():
    """
    Example 6: Demonstrate rate limiting
    """
    print("\n" + "="*60)
    print("Example 6: Rate Limiting")
    print("="*60)

    api_key = os.getenv("OPENAI_API_KEY", "your-api-key-here")
    service = AIPostGenerationService(api_key=api_key, provider="openai")

    print("\nMaking 3 rapid requests to show rate limit tracking:")

    for i in range(3):
        try:
            result = await service.generate_post(
                articles=SAMPLE_ARTICLES[:1],
                platform="twitter",
                user_id=1,
                use_cache=True  # Use cache to speed up
            )

            print(f"\nRequest {i+1}:")
            print(f"  Success: ✅")
            print(f"  Remaining: {result['remaining_requests']}/10 requests")

        except Exception as e:
            print(f"\nRequest {i+1}:")
            print(f"  Error: {str(e)}")


async def example_7_anthropic_provider():
    """
    Example 7: Using Anthropic Claude instead of OpenAI
    """
    print("\n" + "="*60)
    print("Example 7: Anthropic Claude Provider")
    print("="*60)

    api_key = os.getenv("ANTHROPIC_API_KEY", "your-api-key-here")

    # Skip if no Anthropic key
    if api_key == "your-api-key-here":
        print("⚠️ Skipping: No ANTHROPIC_API_KEY set")
        return

    service = AIPostGenerationService(api_key=api_key, provider="anthropic")

    try:
        result = await service.generate_post(
            articles=SAMPLE_ARTICLES[:2],
            platform="linkedin",
            user_id=1,
            use_cache=False
        )

        print(f"\n✅ Generation with Claude Successful!")
        print(f"Provider: {result['metadata']['provider']}")
        print(f"Model: {result['metadata']['model']}")
        print(f"Time: {result['generation_time']}s")
        print(f"\nContent Preview:")
        print(result['content'][:200] + "...")

    except Exception as e:
        print(f"❌ Error: {str(e)}")


async def example_8_error_handling():
    """
    Example 8: Error handling scenarios
    """
    print("\n" + "="*60)
    print("Example 8: Error Handling")
    print("="*60)

    # Test with invalid API key
    print("\nTest 1: Invalid API Key")
    service = AIPostGenerationService(api_key="invalid-key", provider="openai")

    try:
        result = await service.generate_post(
            articles=SAMPLE_ARTICLES[:1],
            platform="twitter",
            user_id=1,
            use_cache=False
        )
        print("  ❌ Should have raised error")
    except Exception as e:
        print(f"  ✅ Correctly caught error: {str(e)[:80]}...")

    # Test with invalid platform
    print("\nTest 2: Invalid Platform")
    api_key = os.getenv("OPENAI_API_KEY", "your-api-key-here")
    service = AIPostGenerationService(api_key=api_key, provider="openai")

    try:
        result = await service.generate_post(
            articles=SAMPLE_ARTICLES[:1],
            platform="invalid-platform",
            user_id=1,
            use_cache=False
        )
        print("  ❌ Should have raised error")
    except Exception as e:
        print(f"  ✅ Correctly caught error: {str(e)[:80]}...")


async def main():
    """Run all examples"""
    print("\n" + "="*60)
    print("AI POST GENERATION SERVICE - EXAMPLES")
    print("="*60)

    examples = [
        ("Basic Generation", example_1_basic_generation),
        ("Multi-Platform", example_2_multi_platform),
        ("Custom Tone", example_3_custom_tone),
        ("Cache Demo", example_4_cache_demonstration),
        ("Validation", example_5_content_validation),
        ("Rate Limiting", example_6_rate_limiting),
        ("Anthropic Provider", example_7_anthropic_provider),
        ("Error Handling", example_8_error_handling),
    ]

    print("\nAvailable Examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")

    print("\nRunning all examples...")
    print("(Set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable)")

    for name, example_func in examples:
        try:
            await example_func()
        except Exception as e:
            print(f"\n❌ Example '{name}' failed: {str(e)}")

    print("\n" + "="*60)
    print("All Examples Complete!")
    print("="*60)


if __name__ == "__main__":
    # Run examples
    asyncio.run(main())
