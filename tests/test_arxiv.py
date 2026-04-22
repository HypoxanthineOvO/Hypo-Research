"""Tests for the arXiv adapter."""

from __future__ import annotations

import httpx
import pytest
import respx

from hypo_research.core.models import SearchParams
from hypo_research.core.sources.arxiv import ArxivSource

SAMPLE_ARXIV_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2301.12345v2</id>
    <updated>2023-01-05T00:00:00Z</updated>
    <published>2023-01-01T00:00:00Z</published>
    <title>
      Cryogenic CMOS for
      Quantum Computing
    </title>
    <summary>
      We present a cryogenic CMOS design...
    </summary>
    <author><name>Alice Smith</name></author>
    <author><name>Bob Jones</name></author>
    <link rel="alternate" href="http://arxiv.org/abs/2301.12345v2"/>
    <arxiv:doi>10.1234/example</arxiv:doi>
    <arxiv:journal_ref>ISSCC 2023</arxiv:journal_ref>
    <arxiv:primary_category term="cs.AR"/>
  </entry>
</feed>
"""

OLD_ARXIV_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/1901.00001v1</id>
    <updated>2019-01-05T00:00:00Z</updated>
    <published>2019-01-01T00:00:00Z</published>
    <title>Legacy cryogenic paper</title>
    <summary>Legacy work.</summary>
    <author><name>Carol Lee</name></author>
    <link rel="alternate" href="http://arxiv.org/abs/1901.00001v1"/>
    <arxiv:primary_category term="cs.AR"/>
  </entry>
</feed>
"""

COMBINED_ARXIV_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2301.12345v2</id>
    <updated>2023-01-05T00:00:00Z</updated>
    <published>2023-01-01T00:00:00Z</published>
    <title>
      Cryogenic CMOS for
      Quantum Computing
    </title>
    <summary>
      We present a cryogenic CMOS design...
    </summary>
    <author><name>Alice Smith</name></author>
    <author><name>Bob Jones</name></author>
    <link rel="alternate" href="http://arxiv.org/abs/2301.12345v2"/>
    <arxiv:doi>10.1234/example</arxiv:doi>
    <arxiv:journal_ref>ISSCC 2023</arxiv:journal_ref>
    <arxiv:primary_category term="cs.AR"/>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/1901.00001v1</id>
    <updated>2019-01-05T00:00:00Z</updated>
    <published>2019-01-01T00:00:00Z</published>
    <title>Legacy cryogenic paper</title>
    <summary>Legacy work.</summary>
    <author><name>Carol Lee</name></author>
    <link rel="alternate" href="http://arxiv.org/abs/1901.00001v1"/>
    <arxiv:primary_category term="cs.AR"/>
  </entry>
</feed>
"""


@pytest.mark.asyncio
@respx.mock
async def test_arxiv_search_maps_fields() -> None:
    source = ArxivSource()
    respx.get("http://export.arxiv.org/api/query").mock(
        return_value=httpx.Response(200, text=SAMPLE_ARXIV_FEED)
    )

    papers = await source.search(SearchParams(query="cryogenic computing", max_results=5))
    await source.close()

    assert len(papers) == 1
    paper = papers[0]
    assert paper.title == "Cryogenic CMOS for Quantum Computing"
    assert paper.authors == ["Alice Smith", "Bob Jones"]
    assert paper.year == 2023
    assert paper.venue == "ISSCC 2023"
    assert paper.abstract == "We present a cryogenic CMOS design..."
    assert paper.doi == "10.1234/example"
    assert paper.arxiv_id == "2301.12345"
    assert paper.url == "http://arxiv.org/abs/2301.12345v2"
    assert paper.citation_count is None


@pytest.mark.asyncio
@respx.mock
async def test_arxiv_title_cleanup() -> None:
    source = ArxivSource()
    respx.get("http://export.arxiv.org/api/query").mock(
        return_value=httpx.Response(200, text=SAMPLE_ARXIV_FEED)
    )

    papers = await source.search(SearchParams(query="cryogenic"))
    await source.close()

    assert papers[0].title == "Cryogenic CMOS for Quantum Computing"


@pytest.mark.asyncio
@respx.mock
async def test_arxiv_client_side_year_filter() -> None:
    source = ArxivSource()
    respx.get("http://export.arxiv.org/api/query").mock(
        return_value=httpx.Response(200, text=COMBINED_ARXIV_FEED)
    )

    papers = await source.search(
        SearchParams(query="cryogenic", year_range=(2020, 2026), max_results=5)
    )
    await source.close()

    assert len(papers) == 1
    assert papers[0].year == 2023


@pytest.mark.asyncio
@respx.mock
async def test_arxiv_id_extraction() -> None:
    source = ArxivSource()
    respx.get("http://export.arxiv.org/api/query").mock(
        return_value=httpx.Response(200, text=SAMPLE_ARXIV_FEED)
    )

    paper = await source.get_paper("2301.12345")
    await source.close()

    assert paper is not None
    assert paper.arxiv_id == "2301.12345"


@pytest.mark.asyncio
async def test_arxiv_get_citations_and_references_return_empty() -> None:
    source = ArxivSource()

    citations = await source.get_citations("2301.12345")
    references = await source.get_references("2301.12345")
    await source.close()

    assert citations == []
    assert references == []


@pytest.mark.asyncio
@respx.mock
async def test_arxiv_handles_empty_response() -> None:
    source = ArxivSource()
    respx.get("http://export.arxiv.org/api/query").mock(
        return_value=httpx.Response(200, text="")
    )

    papers = await source.search(SearchParams(query="cryogenic"))
    await source.close()

    assert papers == []


@pytest.mark.asyncio
@respx.mock
async def test_arxiv_handles_invalid_xml() -> None:
    source = ArxivSource()
    respx.get("http://export.arxiv.org/api/query").mock(
        return_value=httpx.Response(200, text="<html><body>Service error</body></html")
    )

    papers = await source.search(SearchParams(query="cryogenic"))
    await source.close()

    assert papers == []


@pytest.mark.asyncio
@respx.mock
async def test_arxiv_handles_503_status() -> None:
    source = ArxivSource()
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(503, text="Service Unavailable")

    respx.get("http://export.arxiv.org/api/query").mock(side_effect=handler)

    papers = await source.search(SearchParams(query="cryogenic"))
    await source.close()

    assert papers == []
    assert call_count == source.MAX_RETRIES + 1
