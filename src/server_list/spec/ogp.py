#!/usr/bin/env python3
"""
OGP (Open Graph Protocol) tag generation for social media sharing.
"""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urljoin

if TYPE_CHECKING:
    from server_list.config import Config


def escape(text: str) -> str:
    """Escape HTML special characters."""
    return html.escape(str(text)) if text else ""


def generate_ogp_tags(
    title: str,
    description: str,
    url: str,
    image_url: str | None = None,
    site_name: str = "サーバー・仮想マシン一覧",
) -> str:
    """Generate OGP meta tags as HTML string.

    Args:
        title: Page title
        description: Page description
        url: Canonical URL
        image_url: Optional image URL for preview
        site_name: Site name

    Returns:
        HTML string containing OGP meta tags
    """
    tags = [
        f'<meta property="og:title" content="{escape(title)}" />',
        f'<meta property="og:description" content="{escape(description)}" />',
        '<meta property="og:type" content="website" />',
        f'<meta property="og:url" content="{escape(url)}" />',
        f'<meta property="og:site_name" content="{escape(site_name)}" />',
        '<meta name="twitter:card" content="summary" />',
        f'<meta name="twitter:title" content="{escape(title)}" />',
        f'<meta name="twitter:description" content="{escape(description)}" />',
    ]

    if image_url:
        tags.extend([
            f'<meta property="og:image" content="{escape(image_url)}" />',
            f'<meta name="twitter:image" content="{escape(image_url)}" />',
        ])

    return "\n    ".join(tags)


def generate_top_page_ogp(base_url: str, config: Config | None = None) -> str:
    """Generate OGP tags for the top page.

    Args:
        base_url: Base URL of the application
        config: Optional config to get machine count

    Returns:
        HTML string containing OGP meta tags
    """
    machine_count = len(config.machine) if config and config.machine else 0
    vm_count = sum(len(m.vm) if m.vm else 0 for m in config.machine) if config and config.machine else 0

    if machine_count > 0:
        description = (
            f"物理サーバー {machine_count} 台、仮想マシン {vm_count} 台の"
            "インフラストラクチャ情報を一覧表示"
        )
    else:
        description = "サーバー・仮想マシンのインフラストラクチャ情報を一覧表示"

    return generate_ogp_tags(
        title="サーバー・仮想マシン一覧",
        description=description,
        url=urljoin(base_url, "/server-list/"),
    )


def generate_machine_page_ogp(
    base_url: str,
    machine_name: str,
    config: Config | None = None,
    image_dir: Path | None = None,
) -> str:
    """Generate OGP tags for a specific machine page.

    Args:
        base_url: Base URL of the application
        machine_name: Name of the machine
        config: Optional config to get machine details
        image_dir: Optional path to image directory

    Returns:
        HTML string containing OGP meta tags
    """
    machine = None
    if config and config.machine:
        for m in config.machine:
            if m.name == machine_name:
                machine = m
                break

    if machine:
        # Build description from machine specs
        specs = []
        if machine.mode:
            specs.append(machine.mode)
        if machine.cpu:
            specs.append(machine.cpu)
        if machine.ram:
            specs.append(f"RAM: {machine.ram}")
        if machine.vm:
            specs.append(f"VM: {len(machine.vm)}台")

        description = " / ".join(specs) if specs else f"{machine_name} のサーバー情報"
        title = f"{machine_name} - サーバー詳細"

        # Check if image exists
        image_url = None
        if image_dir and machine.mode:
            # Normalize model name for image filename
            image_name = _normalize_model_name(machine.mode)
            for ext in [".png", ".jpg", ".jpeg", ".webp"]:
                image_path = image_dir / f"{image_name}{ext}"
                if image_path.exists():
                    image_url = urljoin(base_url, f"/server-list/api/img/{image_name}{ext}")
                    break
    else:
        title = f"{machine_name} - サーバー詳細"
        description = f"{machine_name} のサーバー情報"
        image_url = None

    return generate_ogp_tags(
        title=title,
        description=description,
        url=urljoin(base_url, f"/server-list/machine/{machine_name}"),
        image_url=image_url,
    )


def _normalize_model_name(model: str) -> str:
    """Normalize model name for image filename lookup.

    Args:
        model: Model name (e.g., "HPE ProLiant DL360 Gen10")

    Returns:
        Normalized name for filename (e.g., "hpe_proliant_dl360_gen10")
    """
    # Convert to lowercase, replace spaces and special chars with underscore
    normalized = model.lower()
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized)
    normalized = normalized.strip("_")
    return normalized


def inject_ogp_into_html(html_content: str, ogp_tags: str) -> str:
    """Inject OGP tags into HTML content.

    Args:
        html_content: Original HTML content
        ogp_tags: OGP meta tags to inject

    Returns:
        HTML content with OGP tags injected
    """
    # Look for </head> or <!-- OGP --> placeholder
    if "<!-- OGP -->" in html_content:
        return html_content.replace("<!-- OGP -->", ogp_tags)

    # Insert before </head>
    if "</head>" in html_content:
        return html_content.replace("</head>", f"    {ogp_tags}\n  </head>")

    # Fallback: return original
    return html_content
