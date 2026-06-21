# How to Build Larry Swordstein (Manual PHB Checklist)

Use this guide to rebuild **Larry Swordstein** in the auto-dm character wizard and verify every line against the **Player’s Handbook (2024)**. Page numbers below come from the PHB PDF that powers this app’s curated data (`data/curated/*.yaml`).

**Target character**

| Field | Value |
|-------|-------|
| Name | Larry Swordstein |
| Species | Human |
| Class | Fighter 1 |
| Background | Soldier |
| Alignment | Neutral Good |
| Campaign | Freeform (notes: planned Eldritch Knight at fighter 3) |

**Wizard flow in the app** (7 steps): Basics → Origin → Abilities → Skills & spells → Features & traits → Starting gear → Review

---

## Before you start — PHB chapter map

| Topic | PHB chapter | Approx. pages |
|-------|-------------|---------------|
| Creating a character, proficiency bonus | Ch. 2 | **19–40** |
| Standard Array | Ch. 2 | **38** |
| Class (Fighter) | Ch. 3 | **102–111** |
| Backgrounds & species | Ch. 4 | **177–196** |
| Origin feats & Fighting Style feats | Ch. 5 | **201–207** |
| Equipment, weapons, armor | Ch. 6 | **213–220+** |

---

## Step 1 — Basics (app wizard)

**PHB:** Ch. 2 (**p. 19–22**) — choose name, species, class, background, alignment.

Enter:

| Field | Larry’s value | PHB check |
|-------|---------------|-----------|
| Name | Larry Swordstein | — |
| Species | Human | Ch. 4, **~p. 194** (Human traits) |
| Class | Fighter | Ch. 3, **p. 102** |
| Background | Soldier | Ch. 4, **p. 184** |
| Alignment | Neutral Good | Ch. 2 / alignment list |
| Campaign setting | Freeform | Homebrew; optional notes for EK plan |

**Human traits to expect on the finished sheet** (Ch. 4, Human):

1. **Resourceful** — Heroic Inspiration when you finish a Long Rest → sheet should show Heroic Inspiration available.
2. **Skillful** — one extra skill proficiency (chosen later).
3. **Versatile** — one extra **Origin feat** of your choice, separate from the background feat (chosen later).

**Soldier background summary** (Ch. 4, **p. 184**):

- Ability score options: **STR, DEX, or CON** (+2 to one, +1 to another).
- Origin feat: **Savage Attacker** (Ch. 5).
- Skills: **Athletics**, **Intimidation**.
- Tool: **Gaming set** (one kind of your choice).
- Equipment: package **A** or **50 GP** (chosen in Step 6).

---

## Step 2 — Origin (app wizard)

**PHB:** Ch. 4 background narrative + Ch. 2 personality (**p. 22–25**).

Larry’s backstory (paraphrased): former city guard who left to pursue knighthood through deeds, not rank. Paste or write equivalent text in **Appearance / notes**.

No mechanical choices here — only flavor.

---

## Step 3 — Abilities (app wizard)

**PHB:** Ch. 2 (**p. 38**) — Standard Array: 15, 14, 13, 12, 10, 8.

### 3a. Base array (before background ASI)

Larry uses a **custom** array tuned for a future Eldritch Knight (INT 14), **not** the app’s one-click “Fighter standard array” button.

| Ability | Larry base | Default app fighter button |
|---------|------------|----------------------------|
| STR | **15** | 15 |
| DEX | **12** | 14 |
| CON | **13** | 13 |
| INT | **14** | 8 |
| WIS | **10** | 10 |
| CHA | **8** | 12 |

Assign manually in the wizard, or edit `base_ability_scores` in the save file.

### 3b. Soldier background ASI (Ch. 4, **p. 177–178** rules; Soldier **p. 184**)

Soldier allows +2/+1 among **STR, DEX, CON**.

Larry’s choices:

- **+2 STR** (15 → **17**)
- **+1 CON** (13 → **14**)

### 3c. Final ability scores

| Ability | Score | Modifier |
|---------|-------|----------|
| STR | 17 | **+3** |
| DEX | 12 | **+1** |
| CON | 14 | **+2** |
| INT | 14 | **+2** |
| WIS | 10 | **+0** |
| CHA | 8 | **−1** |

**Check on sheet:** six scores match the table above.

---

## Step 4 — Skills & spells (app wizard)

**PHB:** Fighter skill list Ch. 3 (**p. 102**); proficiencies Ch. 1 (**p. 9–10**).

### 4a. Fighter — pick 2 skills

Larry chooses:

- **Acrobatics** (DEX)
- **Persuasion** (CHA)

### 4b. Soldier — fixed skills

- **Athletics** (STR)
- **Intimidation** (CHA)

### 4c. Human Skillful — pick 1 skill

Larry chooses:

- **Perception** (WIS)

### 4d. Final skill list (5 proficiencies)

| Skill | Source | Ability | Proficient bonus at L1 |
|-------|--------|---------|------------------------|
| Acrobatics | Fighter | DEX | +1 + 2 = **+3** |
| Persuasion | Fighter | CHA | −1 + 2 = **+1** |
| Athletics | Soldier | STR | +3 + 2 = **+5** |
| Intimidation | Soldier | STR | +3 + 2 = **+5** |
| Perception | Human | WIS | +0 + 2 = **+2** |

**Passive Perception** = 10 + WIS (+0) + proficiency (+2) = **12** (Ch. 1, **p. 10**).

### 4e. Saving throws

Fighter proficient in **STR** and **CON** (Ch. 3, **p. 102**):

- STR save: +3 + 2 = **+5**
- CON save: +2 + 2 = **+4**

### 4f. Spells

Fighter 1 has **no spellcasting**. Cantrips, spells, and spell slots should be empty.

---

## Step 5 — Features & traits (app wizard)

**PHB:** Human choices (Ch. 4); Fighter features (Ch. 3 **p. 103**); Origin feats (Ch. 5 **p. 201+**).

### 5a. Human — Skillful

- **Perception** (already recorded in Step 4).

### 5b. Human — Versatile (second Origin feat)

Larry chooses:

- **Alert** (Ch. 5, **p. 201**)

**Alert effects to verify:**

- **Initiative Proficiency** — add proficiency bonus to Initiative → DEX (+1) + PB (+2) = **Initiative +3**.
- **Initiative Swap** — rules reminder on sheet; not automated in combat.

### 5c. Soldier — background Origin feat

- **Savage Attacker** (Ch. 5, **~p. 202**)

**Effect:** once per turn on a weapon hit, roll damage dice twice and use either result (manual at the table).

### 5d. Fighter — Fighting Style (Ch. 3 **p. 103**; feat text Ch. 5 **~p. 202**)

Larry chooses:

- **Defense** — +1 AC while wearing light, medium, or heavy armor.

> **Manual check note:** PHB Defense should raise Larry’s AC to **17** in chain mail (16 + 1). The app currently computes **AC 16** without applying the Defense fighting style. Verify against the book and note the discrepancy.

### 5e. Fighter — Weapon Mastery (Ch. 3 **p. 103**; properties Ch. 6 **~p. 214+**)

Fighter 1 chooses **3** weapons. Larry picks:

| Weapon | Mastery property | PHB summary |
|--------|------------------|-------------|
| **Greatsword** | **Graze** | On a miss, deal ability-mod damage. |
| **Longsword** | **Sap** | On a hit, target has Disadvantage on its next attack before your next turn. |
| **Spear** | **Sap** | Same as longsword. |

You can change one mastery property after each Long Rest.

### 5f. Class features at level 1 (Ch. 3, **p. 103**)

Confirm these appear under unlocked features / class features:

| Feature | What to check |
|---------|----------------|
| **Fighting Style** | Defense selected |
| **Second Wind** | Bonus Action: regain **1d10 + fighter level** HP; **2 uses**, regain 1 on Short Rest, all on Long Rest |
| **Weapon Mastery** | Three weapons listed above |

---

## Step 6 — Starting gear (app wizard)

**PHB:** Fighter packages Ch. 3 (**p. 102**); Soldier package Ch. 4 (**p. 184**); weapon stats Ch. 6.

### 6a. Fighter starting equipment — **Heavy warrior (A)**

Ch. 3, **p. 102** — option A:

- Chain mail
- Greatsword
- Flail
- 8 javelins
- Dungeoneer’s pack
- **4 GP**

### 6b. Soldier starting equipment — **Soldier’s kit (A)**

Ch. 4, **p. 184** — option A:

- Spear
- Shortbow
- 20 arrows
- Gaming set
- Healer’s kit
- Quiver
- Traveler’s clothes
- **14 GP**

### 6c. Combined inventory (merged packages)

Expect on the sheet:

```
dungeoneer's pack
flail
javelins (8)
spear
shortbow
arrows (20)
gaming set
healer's kit
quiver
traveler's clothes
```

### 6d. Currency

**PHB correct total:** 4 GP (fighter) + 14 GP (soldier) = **18 GP**.

> **Manual check note:** Larry’s save file currently shows **60 GP**. That does not match the PHB packages. Re-check after a fresh preview/save, or correct manually to **18 GP**.

### 6e. Weapons block on sheet

| Weapon | Damage (PHB) | Attack mod (proficient) | Notes |
|--------|----------------|-------------------------|-------|
| Greatsword | **2d6** slashing, Heavy, Two-Handed | +5 (STR +3, PB +2) | Graze mastery |
| Spear | **1d6** piercing, Thrown, Versatile | +5 | Sap mastery |
| Shortbow | **1d6** piercing, Ammunition | +3 (DEX +1, PB +2) | Ranged |

> **Manual check note:** The app’s weapon entry for Greatsword may show **1d12** (greataxe die) instead of PHB **2d6**. Verify against Ch. 6 weapons table (**~p. 214**).

### 6f. Armor & AC

| Item | PHB AC |
|------|--------|
| Chain mail | **16** (no DEX; STR 13+ required — Larry qualifies with STR 17) |
| Defense fighting style | **+1** while armored |
| **Expected total** | **17** |
| Shield | Not equipped |

Speed: **30 ft.** (Human, Ch. 4).

---

## Step 7 — Review & save

**PHB:** Ch. 2 finalize character (**p. 40** area).

Walk the full sheet and confirm:

### Combat stats

| Stat | Expected (PHB) | Larry save / app |
|------|------------------|------------------|
| Level | 1 | 1 |
| Proficiency bonus | **+2** (levels 1–4, Ch. 1 **p. 9**) | +2 |
| Hit Die | d10 | d10 |
| Max HP | 10 + CON mod = **12** | 12 |
| Current HP | 12 | 12 |
| AC | **17** with Defense | **16** in app (see note) |
| Initiative | **+3** (DEX + Alert) | +3 |
| Passive Perception | **12** | 12 |
| Speed | 30 ft. | 30 |

**HP formula (Ch. 3, p. 102):** level 1 = hit die maximum + CON modifier = 10 + 2 = **12**.

### Feats box

Should list:

1. **Savage Attacker** — background Origin feat  
2. **Alert** — Human Versatile Origin feat  
3. **Defense** — Fighting Style feat (from class feature)

### Origin feat effect lines (app summary)

| Feat | Reminder text on sheet |
|------|------------------------|
| Alert | Proficiency on Initiative; Initiative Swap |
| Savage Attacker | Once per turn reroll weapon damage dice on hit |

### Tools & languages

| Entry | Value |
|-------|-------|
| Tool proficiencies | Gaming set |
| Languages | Common |

### Heroic Inspiration

Human **Resourceful** → should have Heroic Inspiration (gained on Long Rest). Larry’s save: `heroic_inspiration: true`.

### Not yet on a level 1 sheet

| Planned | When |
|---------|------|
| Eldritch Knight subclass | Fighter **3** (Ch. 3, **~p. 105**) |
| Action Surge, Tactical Mind | Fighter **2** |
| Extra Attack | Fighter **5** |
| INT-based wizard spells from EK | Fighter **3**+ |

Campaign note in save: *“Planned subclass at fighter 3: Eldritch Knight.”*

---

## Quick “did I miss anything?” checklist

Copy this and tick each box against PHB + app sheet:

- [ ] Name, species, class, background, alignment
- [ ] Base ability array assigned before background ASI
- [ ] Background +2 STR, +1 CON applied
- [ ] Five skills: Acrobatics, Persuasion, Athletics, Intimidation, Perception
- [ ] STR & CON saving throw proficiencies
- [ ] Gaming set tool proficiency
- [ ] Origin feat: Savage Attacker (Soldier)
- [ ] Origin feat: Alert (Human Versatile)
- [ ] Fighting Style: Defense
- [ ] Weapon Mastery: Greatsword (Graze), Longsword (Sap), Spear (Sap)
- [ ] Class features: Second Wind, Weapon Mastery, Fighting Style
- [ ] Fighter gear package A (heavy)
- [ ] Soldier gear package A (kit)
- [ ] Full merged inventory (10 items listed above)
- [ ] **18 GP** (not 60)
- [ ] Chain mail worn, AC **17** with Defense
- [ ] HP **12/12**, Initiative **+3**, Passive Perception **12**
- [ ] Proficiency **+2** displayed
- [ ] Heroic Inspiration from Human Resourceful
- [ ] No spells / slots at level 1

---

## Known app vs PHB gaps (as of this guide)

When manually checking Larry, expect these differences until the app is updated:

1. **Defense fighting style** — PHB +1 AC not added in `compute_ac()` → sheet shows **16** instead of **17**.
2. **Greatsword damage** — PHB is **2d6**; app weapon block may show **1d12**.
3. **Starting gold** — PHB merged total **18 GP**; Larry’s save may still show **60 GP** if currency was edited or not rebuilt from gear packages.
4. **Savage Attacker / Lucky / Healer** — rules text on sheet; damage rerolls and luck points not automated in dice roller.
5. **Eldritch Knight** — subclass and spellcasting not applied until level 3 choice is implemented.

---

## Reference — Larry’s save file

Canonical data: `data/saves/characters/68e38966/character.json`

Key JSON fields for spot checks:

```json
{
  "background_asi_plus2": "str",
  "background_asi_plus1": "con",
  "human_skill": "perception",
  "origin_feat": "Savage Attacker",
  "versatile_origin_feat": "alert",
  "fighting_style_feat": "defense",
  "weapon_mastery": ["greatsword", "longsword", "spear"],
  "class_skill_choices": ["acrobatics", "persuasion"],
  "starting_gear_choice": "heavy",
  "background_gear_choice": "kit"
}
```

---

## PHB page index for Larry’s choices

| What | Page |
|------|------|
| Character creation overview | 19–22 |
| Proficiency bonus (levels 1–4 = +2) | 9 |
| Standard Array | 38 |
| Fighter class & starting gear A/B/C | 102 |
| Fighting Style, Second Wind, Weapon Mastery | 103 |
| Background rules (+2/+1 ASI, feat, skills) | 177–178 |
| Soldier background | 184 |
| Human (Resourceful, Skillful, Versatile) | ~194 |
| Alert | 201 |
| Savage Attacker | ~202 |
| Defense (Fighting Style feat) | ~202 |
| Weapons & mastery properties | 214+ |
| Chain mail (AC 16) | 216 area |

*Page numbers marked ~ are inferred from chapter order when OCR in the glossary did not pin an exact footer; verify against your physical or PDF PHB if a page looks off by one.*
