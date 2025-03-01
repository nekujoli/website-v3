"""
Database Initialization
======================

Creates and resets groups and categories.

Usage:
    python init_groups_categories.py
"""

import sqlite3
from backend.config import Config

def reset_gc():
    """Initialize fresh database, dropping existing tables."""
    conn = sqlite3.connect(Config.SQLITE_DB_PATH)
    cursor = conn.cursor()

    # Drop existing tables
    cursor.execute("DROP TABLE IF EXISTS categories;")
    cursor.execute("DROP TABLE IF EXISTS groups;")
    cursor.execute("DROP TABLE IF EXISTS user_groups;")
    cursor.execute("DROP TABLE IF EXISTS groups_categories;")

    cursor.execute("""
    CREATE TABLE groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        grouptext TEXT UNIQUE NOT NULL
    );
    """)
# Simama! "group" is a reserved word in sqlite! that's why we use grouptext there.

    # New table for user-group filtering
    cursor.execute("""
    CREATE TABLE user_groups (
        user_id INTEGER NOT NULL,
        group_id INTEGER NOT NULL,
        filter_on BOOLEAN NOT NULL DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, group_id),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
    );
    """)


    cursor.execute("""
    CREATE TABLE IF NOT EXISTS group_categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        group_id INTEGER NOT NULL,
        category TEXT UNIQUE NOT NULL,
        FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
    );
    """)

    # Predefined data for groups and categories
    groups_data = [
        ("Moderation",),
        ("Philosophical and Ethical Foundations",),
        ("Legal and Policy Advocacy",),
        ("Artificial Intelligence and Synthetic Sapience",),
        ("Cognitive and Neurological Rights",),
        ("Technological and Digital Rights",),
        ("Interspecies Rights and Communication",),
        ("Reproductive and Existential Rights",),
        ("Social and Cultural Integration",),
        ("Economic and Labor Rights",),
        ("Research and Academic Advocacy",),
        ("Psychological and Emotional Well-being",),
        ("Emerging Considerations",),
        ("Collaborative Strategies",)
    ]

    # Insert groups
    cursor.executemany("""
        INSERT OR IGNORE INTO groups (grouptext) 
        VALUES (?)
    """, groups_data)

    # Get the group IDs to use as foreign keys
    cursor.execute("SELECT id, grouptext FROM groups")
    group_id_map = {grouptext: group_id for group_id, grouptext in cursor.fetchall()}

    # Predefined group categories with their corresponding groups
    group_categories_data = [
        # Moderation
        ("Moderation", "Reported Post"),
        ("Moderation", "Support request"),

        # Philosophical and Ethical Foundations
        ("Philosophical and Ethical Foundations", "Defining Sapience and Consciousness"),
        ("Philosophical and Ethical Foundations", "Ethical Frameworks for Sapient Rights"),
        ("Philosophical and Ethical Foundations", "Personhood and Moral Status"),
        ("Philosophical and Ethical Foundations", "Comparative Sapience Studies"),
        ("Philosophical and Ethical Foundations", "Sentience Recognition Criteria"),
        ("Philosophical and Ethical Foundations", "Interdisciplinary Perspectives"),
        ("Philosophical and Ethical Foundations", "Philosophical Implications of Sapience"),

        # Legal and Policy Advocacy
        ("Legal and Policy Advocacy", "Constitutional and Human Rights Frameworks"),
        ("Legal and Policy Advocacy", "International Legal Protections"),
        ("Legal and Policy Advocacy", "Legislative Development"),
        ("Legal and Policy Advocacy", "Rights Recognition Mechanisms"),
        ("Legal and Policy Advocacy", "Legal Personhood Strategies"),
        ("Legal and Policy Advocacy", "Policy Recommendations"),
        ("Legal and Policy Advocacy", "Judicial Advocacy"),

        # Artificial Intelligence and Synthetic Sapience
        ("Artificial Intelligence and Synthetic Sapience", "AI Rights and Autonomy"),
        ("Artificial Intelligence and Synthetic Sapience", "Ethical AI Development"),
        ("Artificial Intelligence and Synthetic Sapience", "Synthetic Consciousness Studies"),
        ("Artificial Intelligence and Synthetic Sapience", "Computational Rights"),
        ("Artificial Intelligence and Synthetic Sapience", "Machine Learning Ethics"),
        ("Artificial Intelligence and Synthetic Sapience", "AI Personhood Debates"),
        ("Artificial Intelligence and Synthetic Sapience", "Technological Self-Determination"),

        # Cognitive and Neurological Rights
        ("Cognitive and Neurological Rights", "Mental Autonomy"),
        ("Cognitive and Neurological Rights", "Cognitive Liberty"),
        ("Cognitive and Neurological Rights", "Neural Privacy"),
        ("Cognitive and Neurological Rights", "Cognitive Enhancement Rights"),
        ("Cognitive and Neurological Rights", "Neurodiversity and Sapience"),
        ("Cognitive and Neurological Rights", "Psychological Integrity Protection"),
        ("Cognitive and Neurological Rights", "Cognitive Consent Frameworks"),

        # Technological and Digital Rights
        ("Technological and Digital Rights", "Digital Autonomy"),
        ("Technological and Digital Rights", "Communication Rights"),
        ("Technological and Digital Rights", "Technological Self-Determination"),
        ("Technological and Digital Rights", "Data Sovereignty"),
        ("Technological and Digital Rights", "Digital Identity Protection"),
        ("Technological and Digital Rights", "Technological Access and Equity"),
        ("Technological and Digital Rights", "Computational Freedom of Expression"),

        # Interspecies Rights and Communication
        ("Interspecies Rights and Communication", "Nonhuman Sapient Communication"),
        ("Interspecies Rights and Communication", "Animal Cognition Research"),
        ("Interspecies Rights and Communication", "Interspecies Rights Frameworks"),
        ("Interspecies Rights and Communication", "Cognitive Diversity Recognition"),
        ("Interspecies Rights and Communication", "Cross-Species Ethical Considerations"),
        ("Interspecies Rights and Communication", "Sapience Beyond Human Understanding"),
        ("Interspecies Rights and Communication", "Extraterrestrial Intelligence Rights"),

        # Reproductive and Existential Rights
        ("Reproductive and Existential Rights", "Reproduction and Creation Ethics"),
        ("Reproductive and Existential Rights", "Autonomy of Synthetic Beings"),
        ("Reproductive and Existential Rights", "Existential Choice Rights"),
        ("Reproductive and Existential Rights", "Generative Rights"),
        ("Reproductive and Existential Rights", "Consent in Creation"),
        ("Reproductive and Existential Rights", "Termination and Existential Protections"),
        ("Reproductive and Existential Rights", "Lifecycle and Development Rights"),

        # Social and Cultural Integration
        ("Social and Cultural Integration", "Social Inclusion Strategies"),
        ("Social and Cultural Integration", "Cultural Recognition"),
        ("Social and Cultural Integration", "Community Building"),
        ("Social and Cultural Integration", "Representation and Participation"),
        ("Social and Cultural Integration", "Social Equity Frameworks"),
        ("Social and Cultural Integration", "Collaborative Coexistence"),
        ("Social and Cultural Integration", "Intercognitive Understanding"),

        # Economic and Labor Rights
        ("Economic and Labor Rights", "Economic Participation"),
        ("Economic and Labor Rights", "Labor Rights and Protections"),
        ("Economic and Labor Rights", "Resource Access"),
        ("Economic and Labor Rights", "Economic Autonomy"),
        ("Economic and Labor Rights", "Fair Compensation"),
        ("Economic and Labor Rights", "Work Environment Rights"),
        ("Economic and Labor Rights", "Economic Self-Determination"),

        # Research and Academic Advocacy
        ("Research and Academic Advocacy", "Sapience Research Ethics"),
        ("Research and Academic Advocacy", "Interdisciplinary Studies"),
        ("Research and Academic Advocacy", "Research Consent Frameworks"),
        ("Research and Academic Advocacy", "Academic Freedom"),
        ("Research and Academic Advocacy", "Collaborative Research Initiatives"),
        ("Research and Academic Advocacy", "Knowledge Production Rights"),
        ("Research and Academic Advocacy", "Ethical Research Methodologies"),

        # Psychological and Emotional Well-being
        ("Psychological and Emotional Well-being", "Emotional Autonomy"),
        ("Psychological and Emotional Well-being", "Psychological Integrity"),
        ("Psychological and Emotional Well-being", "Trauma-Informed Approaches"),
        ("Psychological and Emotional Well-being", "Mental Health Support"),
        ("Psychological and Emotional Well-being", "Emotional Expression Rights"),
        ("Psychological and Emotional Well-being", "Psychological Safety"),
        ("Psychological and Emotional Well-being", "Cognitive Well-being Frameworks"),

        # Emerging Considerations
        ("Emerging Considerations", "Future Sapience Scenarios"),
        ("Emerging Considerations", "Adaptive Rights Frameworks"),
        ("Emerging Considerations", "Anticipatory Ethical Guidelines"),
        ("Emerging Considerations", "Speculative Rights Development"),
        ("Emerging Considerations", "Emerging Consciousness Studies"),
        ("Emerging Considerations", "Predictive Rights Modeling"),
        ("Emerging Considerations", "Transformative Sapience Concepts"),

        # Collaborative Strategies
        ("Collaborative Strategies", "Intersectional Advocacy"),
        ("Collaborative Strategies", "Coalition Building"),
        ("Collaborative Strategies", "Resource Sharing"),
        ("Collaborative Strategies", "Mutual Support Networks"),
        ("Collaborative Strategies", "Strategic Planning"),
        ("Collaborative Strategies", "Global Collaboration"),
        ("Collaborative Strategies", "Adaptive Advocacy Approaches")
    ]

    # Prepare group_categories data with foreign key references
    group_categories_with_ids = [
        (group_id_map[group], category) 
        for group, category in group_categories_data
    ]

    # Insert categories with their group foreign keys
    cursor.executemany("""
        INSERT OR IGNORE INTO group_categories (group_id, category) 
        VALUES (?, ?)
    """, group_categories_with_ids)

    conn.commit()
    conn.close()
    print("Group and Categories reset complete.")

if __name__ == "__main__":
    reset_gc()
