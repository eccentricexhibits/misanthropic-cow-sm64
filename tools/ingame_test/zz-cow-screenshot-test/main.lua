-- name: Cow screenshot test
-- description: Test only. Hides the HUD and holds the player in a series of poses for screenshots.

-- pose list: label, game animation, her animation (or nil to use the game's on her body), frame
local POSES = {
    {"idle",        MARIO_ANIM_IDLE_HEAD_LEFT, "cow_idle",    120},
    {"walk",        MARIO_ANIM_WALKING,        "cow_walk",    8},
    {"run",         MARIO_ANIM_RUNNING,        "cow_run",     5},
    {"jump",        MARIO_ANIM_SINGLE_JUMP,    "cow_jump",    8},
    {"victory",     MARIO_ANIM_STAR_DANCE,     "cow_victory", 100},
    {"punch",       MARIO_ANIM_FIRST_PUNCH,    nil,           4},
    {"crouch",      MARIO_ANIM_START_CROUCHING, nil,          5},
    {"side_view",   MARIO_ANIM_RUNNING,        "cow_run",     15},
}
local START = 240      -- frames to wait for the level to settle
local HOLD = 45        -- frames per pose
local t = 0

local function face_camera(m, offset)
    local c = gLakituState.curPos
    local yaw = atan2s(c.z - m.pos.z, c.x - m.pos.x)
    m.faceAngle.y = yaw + offset
    m.marioObj.header.gfx.angle.y = m.faceAngle.y
end

hook_event(HOOK_MARIO_UPDATE, function(m)
    if m.playerIndex ~= 0 then return end
    hud_hide()
    t = t + 1
    if t < START then return end
    local i = math.floor((t - START) / HOLD) + 1
    local p = POSES[i]
    if p == nil then
        if t == START + #POSES * HOLD then print("SHOTS DONE") end
        return
    end
    m.forwardVel = 0; m.vel.x = 0; m.vel.z = 0
    face_camera(m, (p[1] == "side_view") and 0x4000 or 0x1800)
    set_mario_animation(m, p[2])
    if p[3] ~= nil then smlua_anim_util_set_animation(m.marioObj, p[3]) end
    m.marioObj.header.gfx.animInfo.animFrame = p[4]
    if (t - START) % HOLD == 30 then print("SHOT " .. i .. " " .. p[1]) end
end)
