// Real art for the office floor — Kenney's CC0 RPG Urban Pack
// (frontend/src/assets/kenney/rpg_urban_pack_extracted/Tiles/, 16x16px
// tiles, no name/index metadata shipped with the pack, so every index below
// was picked by opening the individual tile PNGs and eyeballing them).
//
// Character rows: column 25 is a color variant's "idle" pose, columns 24/26
// are companion poses of the SAME variant (confirmed across multiple rows)
// — used as the two alternating "walk" frames. Row r's triple is
// (27r+24, 27r+25, 27r+26).

import floorTile from '../../assets/kenney/rpg_urban_pack_extracted/Tiles/tile_0081.png'
import deskTile from '../../assets/kenney/rpg_urban_pack_extracted/Tiles/tile_0210.png'

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

// Deterministic per-department color-variant assignment — every client picks
// the same variant for the same department with zero coordination, no
// backend field needed (Agent.avatarSpriteId/character are both hardcoded
// "default" in live data today, so they're not a usable signal yet).
export function variantForDepartment(departmentId: string): CharacterVariant {
  let hash = 0
  for (let i = 0; i < departmentId.length; i++) hash = (hash * 31 + departmentId.charCodeAt(i)) | 0
  const index = Math.abs(hash) % CHARACTER_VARIANTS.length
  return CHARACTER_VARIANTS[index]
}
