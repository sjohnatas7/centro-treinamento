-- 1. Encontre jogadores que participaram de todos os campeonatos de seu esporte em 2023
\echo 1. Encontre jogadores que participaram de todos os campeonatos de seu esporte em 2023
SELECT 
    a.nome,
    t.esporte_nome
FROM 
    atleta a
JOIN 
    atleta_time at ON a.cpf = at.atleta_cpf
JOIN 
    time t ON at.time_id = t.id
JOIN 
    times_participantes tp ON t.id = tp.time_id
JOIN 
    campeonato c ON tp.campeonato_id = c.id AND c.ano = 2023 AND c.esporte_nome = t.esporte_nome
GROUP BY 
    a.cpf, a.nome, t.esporte_nome
HAVING 
    COUNT(DISTINCT c.id) = (
        SELECT COUNT(*)
        FROM campeonato c2
        WHERE c2.ano = 2023
        AND c2.esporte_nome = t.esporte_nome
    );


-- 2. Encontre times que participaram de todos os campeonatos de seu esporte
\echo 2. Encontre times que participaram de todos os campeonatos de seu esporte
SELECT
    t.nome AS team_name,
    t.esporte_nome AS sport_name
FROM
    time t
JOIN
    times_participantes tp ON t.id = tp.time_id
JOIN
    campeonato c ON tp.campeonato_id = c.id AND c.esporte_nome = t.esporte_nome
GROUP BY
    t.id, t.nome, t.esporte_nome
HAVING
    COUNT(DISTINCT c.id) = (
        SELECT COUNT(DISTINCT c2.id)
        FROM campeonato c2
        WHERE c2.esporte_nome = t.esporte_nome
    )
ORDER BY
    t.esporte_nome, t.nome;

-- 3. Encontre times com maior desempenho médio em partidas, incluindo apenas times que participaram de pelo menos 3 partidas
\echo 3. Encontre times com maior desempenho médio em partidas, incluindo apenas times que participaram de pelo menos 3 partidas
SELECT 
    tp.nome,
    tp.avg_performance as media_desempenho,
    tp.num_matches as num_partidas
FROM (
    SELECT 
        t.id,
        t.nome,
        COUNT(pt.partida_id) AS num_matches,
        AVG(pt.desempenho) AS avg_performance
    FROM time t
    JOIN partida_times pt ON t.id = pt.time_id
    GROUP BY t.id, t.nome
    HAVING COUNT(pt.partida_id) >= 3
) tp
WHERE tp.avg_performance = (
    SELECT MAX(sub.avg_performance)
    FROM (
        SELECT 
            t.id,
            t.nome,
            COUNT(pt.partida_id) AS num_matches,
            AVG(pt.desempenho) AS avg_performance
        FROM time t
        JOIN partida_times pt ON t.id = pt.time_id
        GROUP BY t.id, t.nome
        HAVING COUNT(pt.partida_id) >= 3
    ) sub
);

-- 4. Encontre o desempenho médio dos times em campeonatos
\echo 4. Encontre o desempenho médio dos times em campeonatos
SELECT 
    t.nome AS nome_time,
    c.nome AS nome_campeonato,
    AVG(pt.desempenho) AS media_desempenho
FROM 
    time t
JOIN 
    partida_times pt ON t.id = pt.time_id
JOIN 
    partida p ON pt.partida_id = p.id
JOIN 
    campeonato c ON p.campeonato_id = c.id
GROUP BY 
    t.nome, c.nome
ORDER BY 
    t.nome, c.nome;


-- 5. Encontre o número de partidas que cada árbitro apitou em cada esporte
\echo 5. Encontre o número de partidas que cada árbitro apitou em cada esporte
SELECT 
    a.nome as nome_arbitro,
    e.nome as nome_esporte,
    COUNT(p.id) AS number_of_matches
FROM 
    arbitro a
JOIN 
    especialidade_arbitros ea ON a.cpf = ea.arbitro_cpf
JOIN 
    esporte e ON ea.esporte_nome = e.nome
JOIN 
    partida p ON (p.arbitro1_cpf = a.cpf OR p.arbitro2_cpf = a.cpf OR p.arbitro3_cpf = a.cpf)
GROUP BY 
    a.nome, e.nome
ORDER BY 
    a.nome, e.nome;

-- 6. Times que Participaram de Todos os Campeonatos do Seu Esporte
\echo 6. Times que Participaram de Todos os Campeonatos do Seu Esporte
SELECT
    t.nome AS team_name,
    t.esporte_nome AS sport_name
FROM 
    time t
WHERE 
    NOT EXISTS (
        SELECT 
            c.id
        FROM 
            campeonato c
        WHERE 
            c.esporte_nome = t.esporte_nome
        AND 
            NOT EXISTS (
                SELECT 
                    1
                FROM 
                    times_participantes tp
                WHERE 
                    tp.campeonato_id = c.id
                AND 
                    tp.time_id = t.id
            )
    )
ORDER BY 
    t.esporte_nome, t.nome;