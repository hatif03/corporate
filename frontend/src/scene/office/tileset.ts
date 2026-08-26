// Real art for the office floor — Kenney's CC0 RPG Urban Pack
// (frontend/src/assets/kenney/rpg_urban_pack_extracted/Tiles/, 16x16px
// tiles, no name/index metadata shipped with the pack, so every index below
// was picked by opening the individual tile PNGs and eyeballing them —
// rendered at 8x scale with an index grid overlaid, not guessed from the
// packed tilemap thumbnail, which is too small to read reliably).
//
// Character rows: column 25 is a color variant's "idle" pose, columns 24/26
// are companion poses of the SAME variant (confirmed across multiple rows)
// — used as the two alternating "walk" frames. Row r's triple is
// (27r+24, 27r+25, 27r+26).
//
// tile_0210 was previously (wrongly) used as "the desk" — it's actually a
// brick-wall-with-baseboard texture tile, confirmed by rendering it in
// isolation; now correctly used as WALL_TILE below. tile_0300 (a wooden
// dresser/drawer unit) is the closest desk-shaped furniture this pack
// actually has — this pack is an outdoor/urban RPG set, not an
// office-interior set, so there's no literal desk+monitor sprite available;
// a real office-furniture pack (Kenney's Furniture Kit, also CC0) exists
// but renders in a soft-shaded/isometric style that doesn't match this
// pack's flat hard-pixel look, so mixing them would read as visually
// inconsistent rather than more "office-like" — see ADR/plan notes.
// Decorative furniture below (cabinet/plant/trash/art/bookshelf) and the
// wall/door/corridor-floor tiles are all picked the same way — real
// furniture/architecture-shaped tiles, not textures, each individually
// rendered and inspected, not guessed from the packed tilemap thumbnail.

import floorTile from '../../assets/kenney/rpg_urban_pack_extracted/Tiles/tile_0081.png'
import deskTile from '../../assets/kenney/rpg_urban_pack_extracted/Tiles/tile_0300.png'
import cabinetTile from '../../assets/kenney/rpg_urban_pack_extracted/Tiles/tile_0303.png'
import bookshelfTile from '../../assets/kenney/rpg_urban_pack_extracted/Tiles/tile_0304.png'
import plantTile from '../../assets/kenney/rpg_urban_pack_extracted/Tiles/tile_0259.png'
import trashTile from '../../assets/kenney/rpg_urban_pack_extracted/Tiles/tile_0279.png'
import artTile from '../../assets/kenney/rpg_urban_pack_extracted/Tiles/tile_0391.png'
import wallTile from '../../assets/kenney/rpg_urban_pack_extracted/Tiles/tile_0210.png'
import doorTile from '../../assets/kenney/rpg_urban_pack_extracted/Tiles/tile_0405.png'
import corridorFloorTile from '../../assets/kenney/rpg_urban_pack_extracted/Tiles/tile_0419.png'

import char0Idle from '../../assets/kenney/rpg_urban_pack_extracted/Tiles/tile_0025.png'
import char0WalkA from '../../assets/kenney/rpg_urban_pack_extracted/Tiles/tile_0024.png'
import char0WalkB from '../../assets/kenney/rpg_urban_pack_extracted/Tiles/tile_0026.png'

import char1Idle from '../../assets/kenney/rpg_urban_pack_extracted/Tiles/tile_0052.png'
import char1WalkA from '../../assets/kenney/rpg_urban_pack_extracted/Tiles/tile_0051.png'
import char1WalkB from '../../assets/kenney/rpg_urban_pack_extracted/Tiles/tile_0053.png'

import char2Idle from '../../assets/kenney/rpg_urban_pack_extracted/Tiles/tile_0079.png'
import char2WalkA from '../../assets/kenney/rpg_urban_pack_extracted/Tiles/tile_0078.png'
import char2WalkB from '../../assets/kenney/rpg_urban_pack_extracted/Tiles/tile_0080.png'

import char3Idle from '../../assets/kenney/rpg_urban_pack_extracted/Tiles/tile_0106.png'
import char3WalkA from '../../assets/kenney/rpg_urban_pack_extracted/Tiles/tile_0105.png'
import char3WalkB from '../../assets/kenney/rpg_urban_pack_extracted/Tiles/tile_0107.png'

import char4Idle from '../../assets/kenney/rpg_urban_pack_extracted/Tiles/tile_0133.png'
import char4WalkA from '../../assets/kenney/rpg_urban_pack_extracted/Tiles/tile_0132.png'
import char4WalkB from '../../assets/kenney/rpg_urban_pack_extracted/Tiles/tile_0134.png'

import char5Idle from '../../assets/kenney/rpg_urban_pack_extracted/Tiles/tile_0160.png'
import char5WalkA from '../../assets/kenney/rpg_urban_pack_extracted/Tiles/tile_0159.png'
import char5WalkB from '../../assets/kenney/rpg_urban_pack_extracted/Tiles/tile_0161.png'

import char6Idle from '../../assets/kenney/rpg_urban_pack_extracted/Tiles/tile_0187.png'
import char6WalkA from '../../assets/kenney/rpg_urban_pack_extracted/Tiles/tile_0186.png'
import char6WalkB from '../../assets/kenney/rpg_urban_pack_extracted/Tiles/tile_0188.png'

import char7Idle from '../../assets/kenney/rpg_urban_pack_extracted/Tiles/tile_0214.png'
import char7WalkA from '../../assets/kenney/rpg_urban_pack_extracted/Tiles/tile_0213.png'
import char7WalkB from '../../assets/kenney/rpg_urban_pack_extracted/Tiles/tile_0215.png'

export const FLOOR_TILE = floorTile
export const DESK_TILE = deskTile
export const CABINET_TILE = cabinetTile
export const BOOKSHELF_TILE = bookshelfTile
export const PLANT_TILE = plantTile
export const TRASH_TILE = trashTile
export const ART_TILE = artTile
export const WALL_TILE = wallTile
export const DOOR_TILE = doorTile
export const CORRIDOR_FLOOR_TILE = corridorFloorTile

export interface CharacterVariant {
  idle: string
  walkA: string
  walkB: string
}

export const CHARACTER_VARIANTS: CharacterVariant[] = [
  { idle: char0Idle, walkA: char0WalkA, walkB: char0WalkB },
  { idle: char1Idle, walkA: char1WalkA, walkB: char1WalkB },
  { idle: char2Idle, walkA: char2WalkA, walkB: char2WalkB },
  { idle: char3Idle, walkA: char3WalkA, walkB: char3WalkB },
  { idle: char4Idle, walkA: char4WalkA, walkB: char4WalkB },
  { idle: char5Idle, walkA: char5WalkA, walkB: char5WalkB },
  { idle: char6Idle, walkA: char6WalkA, walkB: char6WalkB },
  { idle: char7Idle, walkA: char7WalkA, walkB: char7WalkB },
]

// Deterministic per-department color-variant assignment — fallback for any
// agent that hasn't been given a real persona (Agent.character === "default").
export function variantForDepartment(departmentId: string): CharacterVariant {
  let hash = 0
  for (let i = 0; i < departmentId.length; i++) hash = (hash * 31 + departmentId.charCodeAt(i)) | 0
  const index = Math.abs(hash) % CHARACTER_VARIANTS.length
  return CHARACTER_VARIANTS[index]
}

// Real per-agent persona assignment (scripts/seed.py writes Agent.character
// as "char_0".."char_7") — this is what makes two agents sharing one
// department zone (e.g. ceo + executive, both in the executive room) render
// as visibly distinct people instead of identical department-hash twins.
const CHARACTER_BY_KEY: Record<string, CharacterVariant> = Object.fromEntries(
  CHARACTER_VARIANTS.map((variant, i) => [`char_${i}`, variant]),
)

export function variantForCharacter(character: string, departmentFallback: string): CharacterVariant {
  return CHARACTER_BY_KEY[character] ?? variantForDepartment(departmentFallback)
}
