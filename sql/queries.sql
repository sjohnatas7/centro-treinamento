-- 1. Find players that have participated in all championships of their sport in 2023
\echo 1. Find players that have participated in all championships of their sport in 2023
SELECT a.nome, ac.esporte_nome
FROM (
    SELECT a.cpf, t.esporte_nome, COUNT(DISTINCT c.id) AS championships_participated
    FROM atleta a
    JOIN atleta_time at ON a.cpf = at.atleta_cpf
    JOIN time t ON at.time_id = t.id
    JOIN times_participantes tp ON t.id = tp.time_id
    JOIN campeonato c ON tp.campeonato_id = c.id
    WHERE c.ano = 2023 AND c.esporte_nome = t.esporte_nome
    GROUP BY a.cpf, t.esporte_nome
) ac
JOIN (
    SELECT esporte_nome, COUNT(*) AS total_championships
    FROM campeonato
    WHERE ano = 2023
    GROUP BY esporte_nome
) tc ON ac.esporte_nome = tc.esporte_nome
JOIN atleta a ON ac.cpf = a.cpf
WHERE ac.championships_participated = tc.total_championships;


-- 2. Find teams that have participated in all championships of their sport
\echo 2. Find teams that have participated in all championships of their sport
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

-- 3. Find teams with highest average performance in matches, including only teams that participated in at least 3 matches
\echo 3. Find teams with highest average performance in matches, including only teams that participated in at least 3 matches
SELECT 
    tp.nome,
    tp.avg_performance,
    tp.num_matches
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

-- 4. Find the average performance of teams in championships
\echo 4. Find the average performance of teams in championships
SELECT 
    t.nome AS team_name,
    c.nome AS championship_name,
    AVG(pt.desempenho) AS average_performance
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


-- 5. Find the number of matches each referee has officiated in each sport
\echo 5. Find the number of matches each referee has officiated in each sport
SELECT 
    a.nome AS referee_name,
    e.nome AS sport_name,
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
