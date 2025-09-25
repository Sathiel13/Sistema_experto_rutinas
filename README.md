
<body>
  <h1> Sistema Experto con Experta en py</h1>
  <h1>Le dejo esta pequeña descripcion e instrucciones para que vea que yo realmente se programar, en prolog talvez no pero pyhton es mi fuerte</h1>
  <p>
    En caso de querer usar el modo JSON, se encuentra en la carpeta data y mas abajo su comando de ejecucion
    El codigo base esta en src/engine.py
  </p>
  <p>
    Este proyecto implementa un <strong>Sistema Experto</strong> en Python, 
    diseñado para realizar recomendaciones personalizadas relacionadas con la 
    <em>actividad física</em>. El sistema toma en cuenta factores como:
  </p>
  
  <ul>
    <li>Lesiones previas.</li>
    <li>Preferencias o gustos de entrenamiento.</li>
    <li>Disponibilidad de tiempo.</li>
    <li>Nivel de condición física.</li>
  </ul>

  <h2> ¿Qué es Experta?</h2>
  <p>
    <a href="https://github.com/nilp0inter/experta" target="_blank">Experta</a> 
    es una librería de Python que implementa un motor de inferencia basado en 
    <strong>encadenamiento hacia adelante</strong> (<em>forward chaining</em>), 
    utilizando el algoritmo <em>RETE</em>.  
  </p>

  <div class="highlight">
    <p>
      Con Experta, se pueden definir <strong>hechos</strong> y <strong>reglas</strong> 
      en un <em>KnowledgeEngine</em>. El motor evalúa los hechos disponibles y aplica 
      las reglas que correspondan, generando conclusiones automáticamente.
    </p>
  </div>

  <h2> Estructura del Proyecto</h2>
  <ul>
    <li><code>experta_base.py</code>: Ejemplo simple de uso de la librería Experta para demostrar el encadenamiento hacia adelante.</li>
    <li><code>sistema_experto.py</code>: Implementación del sistema experto de entrenamiento físico.</li>
  </ul>

  <h2> Ejecución</h2>
  <p>Para ejecutar el sistema experto usando el JSON:</p>
  
  <pre><code>python src/engine.py --usuarios data/usuarios.json</code></pre>

  <p>Para ejecutar el sistema experto usando el modo interactivo:</p>
  
  <pre><code>python src/engine.py --interactivo</code></pre>


  <p>
    Asegúrese de tener instalada la librería Experta:
  </p>
  <pre><code>pip install experta</code></pre>

  <h2>Notas</h2>
  <p>
    - El sistema puede extenderse con más reglas, preguntas y recomendaciones personalizadas.
    -Para fines de primera revision me parece bastante completo
  </p>

</body>
</html>
