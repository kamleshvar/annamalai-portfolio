"""Idempotent initial content for the archive.

Only supplied facts are seeded as factual content. Longer biography text is
intentionally written as editable archive copy and can be replaced entirely
from the dashboard. No photographs, screenshots or fake identities are
generated — visual records remain empty until the owner uploads them.
"""
from __future__ import annotations

from flask import current_app

from .extensions import db
from .models import (
    Achievement,
    Admin,
    Collaborator,
    EasterEgg,
    GalleryCategory,
    Organization,
    Profile,
    Project,
    SiteSettings,
)


def seed_database(backfill_access_fragments: bool = False) -> dict[str, int]:
    """Create the initial administrator and supplied archive records.

    Safe to call repeatedly: existing records are never overwritten. Set
    ``backfill_access_fragments`` after upgrading an older database so the
    seeded hidden records receive their default Tempad access fragments.
    """
    created = {
        "admin": 0,
        "profile": 0,
        "achievements": 0,
        "organizations": 0,
        "projects": 0,
        "collaborators": 0,
        "gallery_categories": 0,
        "easter_eggs": 0,
    }

    # --- Administrator ----------------------------------------------------
    if db.session.query(Admin).count() == 0:
        admin = Admin(
            username=current_app.config["ADMIN_USERNAME"],
            must_change_password=True,
        )
        admin.set_password(current_app.config["ADMIN_PASSWORD"])
        db.session.add(admin)
        created["admin"] = 1

    # --- Profile ----------------------------------------------------------
    if db.session.query(Profile).count() == 0:
        profile = Profile(
            name="ANNAMALAI",
            role_line="DEVELOPER. CREATOR. COLLABORATOR.",
            tagline="Always building something beyond the ordinary.",
            intro=(
                "Welcome to my personal timeline. I am a developer, creator and "
                "collaborator — and this archive is where the work, the teams and "
                "the moments in between are kept."
            ),
            biography=(
                "Some stories are told in chapters. This one is told in timelines.\n\n"
                "I build things, coordinate teams, and collaborate with people who "
                "care about turning ideas into something real. The archive records "
                "the projects, the achievements, the people and the work still in motion.\n\n"
                "This is not a finished story. It is a living record, updated from "
                "the control room as the timeline continues."
            ),
            philosophy="Build with intention. Leave a signal.",
            focus_areas="DEVELOPMENT / TEAMS / COLLABORATION",
            location="",
            email="",
            phone="",
        )
        db.session.add(profile)
        created["profile"] = 1

    # --- Site settings ----------------------------------------------------
    if db.session.query(SiteSettings).count() == 0:
        settings = SiteSettings(
            site_title="ANNAMALAI",
            site_subtitle="PERSONAL DIGITAL UNIVERSE",
            archive_code="ARCHIVE // A-001",
            meta_description=(
                "The personal digital universe of Annamalai — a living archive of "
                "projects, achievements, teams, collaborators, memories and signals."
            ),
            hero_kicker="PERSONAL ARCHIVE / TIMELINE A-001",
            hero_line_1="EVERY TIMELINE HAS A STORY.",
            hero_line_2="THIS ONE IS MINE.",
            hero_description=(
                "Developer. Creator. Collaborator. Always building something "
                "beyond the ordinary."
            ),
            about_heading="MORE THAN JUST CODE.",
            about_note="a living archive, not a finished story.",
            achievements_heading="MARKS ON THE TIMELINE.",
            achievements_intro="Coordinates where effort became a result.",
            teams_heading="THE PEOPLE AND TEAMS BEHIND THE WORK.",
            teams_intro=(
                "Organizations, roles, and the shared work that shapes the archive."
            ),
            projects_heading="THINGS I BROUGHT INTO EXISTENCE.",
            projects_intro=(
                "A record of ideas that became real, and the work still in motion."
            ),
            people_heading="THE PEOPLE IN MY TIMELINE.",
            people_intro=(
                "Collaborators, builders, and the company that makes the work matter."
            ),
            gallery_heading="FRAGMENTS OF MEMORY.",
            gallery_intro=(
                "A visual archive of moments, milestones and the spaces between."
            ),
            control_heading="THE ARCHIVE CONTROL SYSTEM.",
            control_intro=(
                "A live interface into the records that power this universe. "
                "Every control is real."
            ),
            contact_heading="SEND A SIGNAL.",
            contact_intro=(
                "Have a project, an idea, or a timeline worth crossing? "
                "The archive is listening."
            ),
            footer_note=(
                "NOT JUST A PORTFOLIO. A TIMELINE OF EVERYTHING I AM BUILDING."
            ),
            footer_hint="SOME RECORDS ARE HIDDEN. THE ARCHIVE REWARDS ATTENTION.",
        )
        db.session.add(settings)

    # --- Achievements -----------------------------------------------------
    if db.session.query(Achievement).count() == 0:
        achievements = [
            Achievement(
                title="PS SENIOR — BINARY BLITZ",
                position="1ST PLACE",
                year="",
                description=(
                    "First place at PS Senior — Binary Blitz. The visual record "
                    "and field notes for this event can be added from the control room."
                ),
                sort_order=1,
            ),
            Achievement(
                title="SRM CODATHON 2025",
                position="3RD PLACE",
                year="2025",
                description=(
                    "Third place at SRM Codathon 2025. The visual record and field "
                    "notes for this event can be added from the control room."
                ),
                sort_order=2,
            ),
            Achievement(
                title="SRM CODATHON 2026",
                position="4TH PLACE",
                year="2026",
                description=(
                    "Fourth place at SRM Codathon 2026. The visual record and field "
                    "notes for this event can be added from the control room."
                ),
                sort_order=3,
            ),
            Achievement(
                title="SANDIPANI VIDYALAYA SHARK TANK",
                position="2ND PLACE",
                year="",
                description=(
                    "Second place at Sandipani Vidyalaya Shark Tank. The visual "
                    "record and field notes for this event can be added from the control room."
                ),
                sort_order=4,
            ),
        ]
        db.session.add_all(achievements)
        created["achievements"] = len(achievements)

    # --- Organizations ----------------------------------------------------
    if db.session.query(Organization).count() == 0:
        organizations = [
            Organization(
                name="BTGR",
                role="COORDINATOR",
                description=(
                    "Organization record. Role: Coordinator. Description, logo and "
                    "external coordinates can be added from the control room."
                ),
                website="",
                sort_order=1,
            ),
            Organization(
                name="TECHORIGIN",
                role="CO-FOUNDER",
                description=(
                    "Organization record. Role: Co-Founder. Description, logo and "
                    "external coordinates can be added from the control room."
                ),
                website="",
                sort_order=2,
            ),
        ]
        db.session.add_all(organizations)
        created["organizations"] = len(organizations)

    # --- Projects ---------------------------------------------------------
    if db.session.query(Project).count() == 0:
        friendshare = Project(
            title="FRIENDSHARE",
            tagline="A live project, recorded in the archive.",
            description=(
                "FriendShare is an active project by Annamalai. Visit the live "
                "project to experience it directly. Screenshots, build notes and "
                "technology records will appear here as they are added from the "
                "control room."
            ),
            long_description=(
                "The live site is the authoritative record of FriendShare. This "
                "archive entry holds the project's visual and technical documentation; "
                "no feature claims are made until the owner records them here."
            ),
            tech_stack="",
            external_url="https://friendshare.techorigin.online",
            github_url="",
            featured=True,
            sort_order=1,
        )
        db.session.add(friendshare)
        created["projects"] = 1

    # --- Collaborators ----------------------------------------------------
    if db.session.query(Collaborator).count() == 0:
        collaborators = [
            Collaborator(
                name="ARVINDHAN",
                description="",
                website="https://arvindhan.com",
                sort_order=1,
            ),
            Collaborator(
                name="KAMLESHVAR",
                description="",
                website="https://kamleswar.online",
                sort_order=2,
            ),
            Collaborator(
                name="ABINAAV",
                description="",
                website="https://abinaav.com",
                sort_order=3,
            ),
            Collaborator(
                name="GOKUL",
                description="",
                website="https://gokul.netlify.com",
                sort_order=4,
            ),
        ]
        db.session.add_all(collaborators)
        created["collaborators"] = len(collaborators)

    # --- Gallery categories (no fake photographs) -------------------------
    if db.session.query(GalleryCategory).count() == 0:
        categories = [
            GalleryCategory(
                name="Experiences",
                slug="experiences",
                description="Personal moments and places, archived as they happen.",
                sort_order=1,
            ),
            GalleryCategory(
                name="People & Teams",
                slug="people-teams",
                description="The faces and teams connected to the work.",
                sort_order=2,
            ),
            GalleryCategory(
                name="Milestones",
                slug="milestones",
                description="Events, wins and coordinates marked on the timeline.",
                sort_order=3,
            ),
        ]
        db.session.add_all(categories)
        created["gallery_categories"] = len(categories)

    # --- Easter eggs / hidden records ------------------------------------
    if db.session.query(EasterEgg).count() == 0:
        eggs = [
            EasterEgg(
                key="temporal-artifact",
                title="THE ARTIFACT REMEMBERS",
                message=(
                    "Artifact A-001 recognises you. Every timeline contains a version "
                    "of you that never made it into the archive. This one did. Keep building."
                ),
                section="hero",
                interaction_type="artifact",
                sort_order=1,
            ),
            EasterEgg(
                key="margin-note",
                title="MARGIN NOTE / UNFILED",
                message=(
                    "The story is never only the highlight reel. The margin notes — "
                    "the failed builds, the late revisions, the quiet decisions — are "
                    "where the real work lives."
                ),
                section="about",
                interaction_type="document",
                access_code="ORIGIN",
                access_slot=1,
                sort_order=2,
            ),
            EasterEgg(
                key="timeline-mark",
                title="THE MARK IS A COORDINATE",
                message=(
                    "A result is a coordinate, not a destination. Save the position, "
                    "then keep moving through the timeline."
                ),
                section="achievements",
                interaction_type="hidden",
                access_code="SIGNAL",
                access_slot=2,
                sort_order=3,
            ),
            EasterEgg(
                key="people-document",
                title="CONSTELLATION RECORD",
                message=(
                    "Every archive is a constellation of people. None of this happened "
                    "alone. The names in this record matter as much as the work."
                ),
                section="people",
                interaction_type="document",
                sort_order=4,
            ),
            EasterEgg(
                key="unseen-frame",
                title="THE UNSEEN FRAME",
                message=(
                    "Not every memory is photographed. The ones that are have learned "
                    "to wait in the dark until someone opens the archive."
                ),
                section="gallery",
                interaction_type="hidden",
                access_code="ECHO",
                access_slot=3,
                sort_order=5,
            ),
            EasterEgg(
                key="control-frequency",
                title="FREQUENCY 07",
                message=(
                    "The control room sees you. Every panel is connected to a real "
                    "record. Try the terminal. Try the keys. The archive keeps its promises."
                ),
                section="control",
                interaction_type="terminal",
                sort_order=6,
            ),
            EasterEgg(
                key="footer-signal",
                title="EDGE OF THE PUBLIC ARCHIVE",
                message=(
                    "You found the edge of the public archive. There is more behind "
                    "the console: a hidden frequency, a dormant artifact, and records "
                    "that only appear to the curious."
                ),
                section="footer",
                interaction_type="hidden",
                access_code="VARIANT",
                access_slot=4,
                sort_order=7,
            ),
            EasterEgg(
                key="terminal-welcome",
                title="TERMINAL HANDSHAKE",
                message=(
                    "ARCHIVE TERMINAL v2.1 — connection accepted. Type HELP to list "
                    "commands. The interface remembers nothing, but the archive remembers everything."
                ),
                section="global",
                interaction_type="terminal",
                sort_order=8,
            ),
        ]
        db.session.add_all(eggs)
        created["easter_eggs"] = len(eggs)

    # Older archive databases predate the Tempad puzzle. When the schema
    # upgrade has just added the fragment columns, give the four seeded records
    # their default fragments without touching any other editable content.
    if backfill_access_fragments:
        fragment_backfill = {
            "margin-note": ("ORIGIN", 1),
            "timeline-mark": ("SIGNAL", 2),
            "unseen-frame": ("ECHO", 3),
            "footer-signal": ("VARIANT", 4),
        }
        for key, (code, slot) in fragment_backfill.items():
            egg = EasterEgg.query.filter_by(key=key).first()
            if egg and not egg.access_code and not egg.access_slot:
                egg.access_code = code
                egg.access_slot = slot

    db.session.commit()
    return created
